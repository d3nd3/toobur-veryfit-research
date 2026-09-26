# Custom firmware on the Toobur A200 — feasibility

Answers "can I flash custom firmware onto this watch?" — live-probe evidence plus
the Realtek DFU stack recovered from the vendor's own Android SDK.

**Verdict:** the *protocol* has no firmware-signature check, so a modified Realtek
image is flashable in principle. On **this** A200 firmware the OTA entry point is
stubbed out, so BLE-only flashing is currently a dead end. The realistic route is
the **Realtek UART/ROM bootloader on the PCB**, which bypasses BLE entirely.

Live session: 2026-09-26, `F9:24:12:2E:0C:32` "Band 8", fw 17, battery 32 %.

---

## 1. Hardware identity

| Property | Value | Source |
|---|---|---|
| Advertised name | `Band 8` | live scan |
| MAC | `F9:24:12:2E:0C:32` | live |
| Manufacturer ID | `0x0214` (532) | ad `ManufacturerData` |
| Services | `0x0AF0` (IDO/Realtek), `0x1800`, `0x1801` | live GATT |
| `device_id` | `532` | `GET 02 01`, vault `GetDeviceInfo.md` |
| `firmware_version` | `17` (`0x11`) | `GET 02 01` byte 4 + ad `02 02 11` |
| `platform` | `40` | vault `GetDeviceInfo.md` |
| `bootload_version` | `0` | vault |
| MTU | `137` (`0x89`) | `GET 02 F0` |

SoC is a **Realtek BLE part** (RTL8762 class per the vault's hardware note), and
the vendor stack is Realtek's, not Nordic's — the `0x0AF0` service is Realtek's
IDI BLE service.

## 2. GATT in normal mode

Live dump: [`2026-09-26_092625_gatt-dump.txt`](../packetdumps/live/2026-09-26_092625_gatt-dump.txt)

| Service | Chars |
|---|---|
| `00000af0` | `0af6` write (normal) · `0af7` notify · `0af1` write (bulk) · `0af2` notify (bulk) |
| `00001800` | `2a00` device name · `2a01` appearance · `2aa6` central address res · `2ac9` client char res |
| `00001801` | `2a05` service changed (indicate) |

**No Realtek DFU or OTA service is exposed in normal mode** — confirmed twice,
including right after an OTA-start command.

## 3. The Realtek DFU stack *is* in the vendor SDK

`research/repositories/IDOAndroidBleSDK/libs/IDoBLELib-Custom-2.46.4.jar` bundles
Realtek's official DFU SDK under `com.realsil.sdk.dfu` (decompile with
`jadx`). This is the whole update path, not a stub.

**GATT profile** — `com.realsil.sdk.dfu.core.gatt.GattDfuProfile`:

| UUID | Role |
|---|---|
| `00006287-3c17-d293-8e48-14fe2e4da212` | DFU service |
| `00006387-…` | DFU data |
| `00006487-…` | DFU control point |
| `00006587-…` | DFU extend flash |
| `0000d0ff-3c17-d293-8e48-14fe2e4da212` | OTA service |
| `0000ffd0-…` / `0000ffd1-…` … `0000ffd8-…`, `0000fff1-…`, `0000fff2-…` | OTA v0 service + control / MAC / patch ver / app ver / test mode / device info / image counter |

Control-point opcodes: `01` start-DFU, `02` receive-image, `03` validate,
`04` activate+reset, `05` reset, `06` report-target-image-info, `07` conn-param,
`08` in-busy, `09` enable-buffer-check, `0A` report-buffer-CRC, `0B` report-IC-type,
`0C` copy-image, `0D` device-info.

`GET 02 A7` (flash-bin info) **does** reply on this A200:
`02 A7 00 01 01 78 56 34 12` — 6 payload bytes, trailing `78 56 34 12` reading
little-endian as the placeholder-ish `0x12345678`.

Field layout is **unconfirmed**. `FlashBinInfo` is declared
`{status, version, matchVersion, checkCode}` but `com.ido.ble.protocol.handler.o`
parses it with `Gson.fromJson(...)` — i.e. the SDK expects a **JSON** reply, and
this 6-byte binary answer does not match. Either `A7` uses a second, binary reply
format on A200, or the observed bytes are an ACK and the real payload is dropped.
Do not build tooling on the assumed `00 01 01 78 56 34 12` split without a capture
that shows the app rendering it.

## 4. Security posture — this is the good news

Three gates exist, and **none of them is a signature**:

1. **No signature verification anywhere in the client stack.**
   `ImageValidateManager.check()` only does structural checks (pack vs single file,
   duplicate bank, missing OTA-header / ROM-patch / app image, version ordering).
   No RSA, ECDSA, or HMAC over the image exists in the SDK.

2. **The "auth" is a version handshake, not a secret.**
   `com.ido.ble.dfu.rtk.auth.RtkAuthTask` builds the auth parameter from the
   *firmware file being flashed*:
   ```java
   authPara.deviceId = getVersionFromBinFile();   // ((imageVersion >> 12) & 0x7FFF), bit15 if reserved>0
   y.b(c.b(gson.toJson(authPara)), 407);          // 407 = wire 01 03
   ```
   The device replies JSON `{errCode}`; `errCode == 0` passes. Since the claimed
   value is read out of our own file's header, it is trivially forgeable — there is
   no key to steal.

3. **AES-256 is negotiated, not mandatory.**
   `OtaDeviceInfo.isAesEncryptEnabled()` is derived from a bit the *device* reports
   (`be = (mode >> 1) & 1`). Where it is off, `e/c.java` ships the image in
   **plaintext**. Where it is on, blocks are run through `AesJni.aesEncrypt` in
   16-byte ECB units with a 32-byte key from `libAesJni.so` — a lib **not shipped**
   in this SDK, so the plaintext path is what the vendor tooling actually exercises.

Practical consequence: a stock image that has been patched, with its CRC16 and
`imageSize` header fields fixed up, has no cryptographic obstacle. The obstacles are
knowing the format well enough and getting the bytes onto the chip.

## 5. Firmware image format

A `.zip` (the SDK's `firmware.zip`) of Realtek "bin" images. Each image starts with
a 12-byte **little-endian** header — recovered from `h/a.java` (BBPRO family),
`h/b.java` (BEE1), `h/c.java` (BEE2):

| Off | Size | BBPRO (`icType` 4/6/7/8) | BEE1 (`icType` 3) | BEE2 (`icType` 5/9) |
|---|---|---|---|---|
| 0 | 1 | `icType` | `flashAddr` lo | `icType` |
| 1 | 1 | `otaFlag` | `flashAddr` hi | `secureVersion` |
| 2 | 2 | `imageId` | `imageId` | (reserved) |
| 4 | 2 | (reserved) | `imageVersion` | `imageId` |
| 6 | 2 | `crc16` | `crc16` | `crc16` |
| 8 | 4 | `imageSize` | `imageSize` (words) | `imageSize` |

`imageId` `0x0200` = ROM/patch, `0x0300` = app. `0x800` (2048) marks the OTA
header / bank-switch image. Version formats are BCD-ish and selectable
(`BinIndicator.VersionFormat` 1–7). Banks are A/B with a copy-image opcode.

`imageVersion` bit layout (from `getVersionFromBinFile`):
`[31:27] reserved · [26:12] build · [11:4] minor · [3:0] major`.

## 6. Live probes — where it stops

| Command | Reply | Meaning |
|---|---|---|
| `04 01 F1 01 01 02 02 01 00` | `04 01 00 00` | **bind OK** (`bind_ret_code=0`, `auth_length=0`) |
| `04 01` + Gson `BindPara` JSON | *silent* | watch wants **binary**, not JSON, on `0x0AF0` |
| `01 01` | `01 01 00 01 07 00` | `err=0` = success per `m.java:11` … **but no mode switch** |
| `01 02`, `01 03` (±JSON/binary), `01 04`–`01 07`, `01 00` | *silent* | no OTA-family reply at all |
| `02 48` (firmware status) | *silent* | matches earlier sessions |

Binding was tried **before and after** `01 01`; identical outcome. After `01 01`
the watch was observed for 40 s and reconnected: still `Band 8`, same MAC, same
three services, no `0x6287`/`0xd0ff`. It simply does not reboot into the Realtek
bootloader — see [`2026-09-26_093546_ota-watch.txt`](../packetdumps/live/2026-09-26_093546_ota-watch.txt).

The func table advertises `deviceUpdate` (vault `FuncTables.md`, table 0 bit 4), so
the capability is *claimed*; the A200 firmware evidently stubs or server-gates it.
Most likely the real app only reaches this after a signed cloud handshake
(`CheckNewVersionPara` → `NewVersionInfo.url` → `firmware.zip`), which is exactly
the part we do not have.

**Prerequisite that did matter:** the watch ignores GETs until the VeryFit connect
prelude runs — `02 01`, `02 02`, `02 07`, `02 F0`, then v3 `…1A…`. Without it
every probe is silent, which is what made this look like a dead device.

### Side effect: the watch is now bound to this host

The `04 01` bind during testing was not a no-op. The `GET 02 01` reply changed
across the session:

```
before bind:  02 01 14 02 11 01 00 20 00 01 01 00 28 02 01 03 03
after  bind:  02 01 14 02 11 01 00 20 01 01 01 00 28 02 01 03 03
                                        ^^
```

One payload byte flipped `00` → `01`. `BasicInfo` is the model behind `02 01`
and its only bind-state field is `pairFlag` (`PAIR_FLAG_BIND = 1`,
`PAIR_FLAG_NOT_BIND = 0`), so the watch is now **bound to the Linux host** rather
than to the phone. Exact byte→field mapping is parsed in native code
(`WriteJsonData`'s counterpart), so the index is not confirmed — the before/after
delta is.

Recovery, per the IDO binding docs: with the phone disconnected, the app performs a
*disconnection-side* rebind, which clears the binding **without erasing data**. Only
a *connected-side* unbind (`04 02`) wipes the watch. So re-pairing from the app is
safe. Do not send `04 02` from a host.

## 7. Paths forward, best first

1. **UART/ROM bootloader (recommended).** Realtek RTL8762 parts boot from a serial
   ROM/ISP path on test pads. Open the case, find the TX/RX/EN pads, and flash with
   a 3.3 V USB-TTL adapter. This bypasses the stubbed BLE path entirely and is the
   standard way these watches get custom firmware. *No BLE OTA needed.* Expect to
   lose the BLE-only niceties unless the image is a full Realtek app build.
   See §7.1 for what the eFuse security model means for this.
2. **Recover a stock image, then patch it.** Capture `firmware.zip` from the VeryFit
   cloud (or dump flash over UART). With the header layout in §5 and no signature
   (§4), repacking a modified image is tractable.
3. **Custom watch face — no firmware at all.** A `.iwf` dial is code the watch
   executes. This is the best "my own software" option that avoids reflashing, and
   the file-transfer channel is already half-open. See
   [`screen_payloads.md`](screen_payloads.md).
4. **A different firmware revision.** Some VeryFit SKUs ship the un-stubbed Realtek
   DFU. If a `firmware.zip` for a sibling model exists, its `icType` may match and
   the DFU path may open up.

### Do not

- `04 02` (unbind) — the IDO docs state an **unbind while connected erases all
  watch data**. Bind/unbind asymmetry, not worth it for a firmware experiment.

### 7.1 What the RTL8762CKF playbook does and does not give us

`chipolino/The_Playbook/Realtek.md` documents a power-glitch attack that unlocks
SWD on an **RTL8762CKF**, bypassing the bootrom's password check
(`configure_security_register_and_LOCK_it()` → `check_password()`), using
Chip'olino's EM side-channel to time a glitch on the VDIGI rail.

**Not applicable as written.** That part is bare silicon soldered onto Realtek's
own evaluation addon board, where SWD is bonded out to a header. A watch has the
SoC in a BGA package with no debug header; the pads are either unpopulated or
absent. You cannot attach an EM probe to a wristwatch. The attack is a
dev-board-to-dev-board technique.

**But the security-level table is the genuinely useful part.** RTL8762C parts
carry 6 eFuse-backed security levels controlling four things, and two rows matter:

| | levels 0–2 | levels 3–5 |
|---|---|---|
| **HCI Download** (the UART/ISP bootloader) | **Enable** | **Enable by password** |
| eFuse Read | Enable / by password | Enable (lvl 3,4) / Disable (lvl 5) |

This reframes route 1 usefully. The ISP bootloader that would flash your custom
firmware is *always present*. It is either open, or gated by a **download
password** — and a password is a finite, attackable obstacle, unlike a signature.
The playbook also notes that password verification is AES-based over **16 eFuse
cells**, and that at levels where eFuse *read* is permitted without a password,
the password itself can be read out. So the chain is:

> identify the security level → try ISP with no password → if prompted, try to
> read eFuse for the download password → otherwise brute-force / glitch

That is a real, ordered plan rather than "impossible". It does need the case open
and a UART adapter, and possibly a glitch rig — but the first two steps are
ordinary bench work.

Caveat: this table is documented for RTL8762**C**KF specifically. The A200's exact
SKU is not confirmed from BLE (the app only reports `platform=40`), so treat the
levels as indicative until the chip markings are read off the board.


## 8. Tooling added

| Script | Purpose |
|---|---|
| [`scripts/toobur_hello_world.py`](../scripts/toobur_hello_world.py) | **works** — put arbitrary text on the screen via `MSG 05 03` |
| [`scripts/toobur_gatt_dump.py`](../scripts/toobur_gatt_dump.py) | scan → connect → full GATT tree; flags Realtek DFU/OTA UUIDs. `--prelude` runs the connect prelude, `--ota` sends `01 01` and re-probes |
| [`scripts/toobur_ota_watch.py`](../scripts/toobur_ota_watch.py) | sends an OTA command, then scans and reports every device + GATT to catch a reboot |
| [`scripts/toobur_bulk_probe.py`](../scripts/toobur_bulk_probe.py) | drives the `D1` file-transfer handshake (announce/start/data/finish) and lists dials |

Both `toobur_gatt_dump.py` and `toobur_ota_watch.py` handle the A200's bursty
advertising: BlueZ reaps the device object between bursts, so the connect path
re-discovers on every attempt.

## Related

- [`screen_payloads.md`](screen_payloads.md) — **start here**: the working
  text-on-screen route and the half-open custom-watch-face channel
- [`docs/firmware_ota.md`](firmware_ota.md) — status board for the IDO-level OTA pipe
- [`docs/watch_faces_v3.md`](watch_faces_v3.md) — `.iwf` upload path
- [`A200-PROTOCOL.md`](../A200-PROTOCOL.md) — canonical wire map

