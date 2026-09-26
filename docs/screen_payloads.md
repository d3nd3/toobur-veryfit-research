# Putting your own content on the Toobur A200 screen

Three routes, ranked by how much is already proven working. Short version:
**route 1 works today**, route 2 is half-open, route 3 needs hardware.

Live session: 2026-09-26, `F9:24:12:2E:0C:32` "Band 8", fw 17, battery 32 %,
MTU 137.

---

## Route 1 — Arbitrary text via the message channel ✅ WORKS

The watch renders `MSG 0x05 0x03` payloads on screen as notifications, using its
own font renderer. That is the cheapest "hello world" that exists on this device,
and it is **verified live**.

### Wire format

From `TooburMsgPackets.encodeMessageBody` / `buildChunkWire`:

```
body  = type | len(text) | len(phone) | len(title) | phone | title | text
chunk = 05 03 | totalChunks | idx (1-based) | 16 B slice (zero-padded)
```

Field caps (angelfit `protocol_notice_s`): title 100 B, body 100 B, phone 20 B —
all UTF-8. Icon `type` is `1` generic, `3` WeChat, `8` WhatsApp, `10` Instagram…

### Verified exchange

```
TX 05 03 02 01 08 0B 00 10 48 65 6C 6C 6F 20 66 72 6F 6D 20 4C
RX 05 03 02 01 00 00 …            status 0x00 = accepted
TX 05 03 02 02 69 6E 75 78 48 45 4C 4C 4F 20 57 4F 52 4C 44 00
RX 05 03 02 02 00 00 …            status 0x00 = accepted
```

`type=08` (WhatsApp icon), `title="Hello from Linux"`, `text="HELLO WORLD"`.

### Use it

```bash
python3 scripts/toobur_hello_world.py --title "Hello from Linux" --body "HELLO WORLD" --type 8
python3 scripts/toobur_hello_world.py --body "any text, 100 bytes max" --repeat 3
python3 scripts/toobur_hello_world.py --call --title "Alice" --phone "+441234567890"
```

`--call` uses the incoming-call form (`05 01`, payload `len(phone) | len(name) | phone | name`),
which pops a full-screen caller card and keeps re-rendering — the most
conspicuous "hello world" available. Body caps at 100 bytes; the script refuses
nothing but you should keep to the documented limits.

### What this is and is not

The text is rendered by the **vendor's** notification code. You are not running
your own code. But it is arbitrary attacker-chosen text on the screen, driven
from a Linux host over BLE, with no app and no cloud.

## Route 2 — Custom watch face (`.iwf`) ⚠️ PARTIALLY WORKING

A dial *is* code the watch executes (a layout the firmware's renderer
interprets), so a custom face is the closest thing to "my software" that does
not need a reflash. Two of the three sub-pieces now work.

### 2b. The `.iwf` container — see [`iwf_format.md`](iwf_format.md)

A real 52,129-byte A200 face has been extracted from the app's own upload
(`packetdumps/extracted/upload.iwf`) and analysed. Confirmed: `iwf\0` magic,
version 1, entry count, the `RAW\0` RGB565 image codec, and a **120 × 240**
screen. Not confirmed: the A200 TOC layout (differs from the published spec) and
the per-entry compression. Full write-up in [`iwf_format.md`](iwf_format.md).

### 2c. Dial list + switching — WORKS ✅ (confirmed on the watch)

v3 `0x0006` returns the installed dials, v3 `0x0008` activates one by name. No
file upload involved. **Confirmed working: the user watched the face change to a
red/green dial after a `0x0008` set.**

```
TX 33 DA AD DA AD 01 0B 00 06 00 00 02 EA EB
RX 33 DA AD DA AD 01 36 00 06 00 00 02 01 03 00 01 00 1C 01 01 07 00 00 00
   6C 6F 63 61 6C 5F 31  01 07 00 00 00 6C 6F 63 61 6C 5F 32  01 07 00 00 00
   6C 6F 63 61 6C 5F 33 18 0E
```

Decoded: **3 dials, all `type=1`, named `local_1`, `local_2`, `local_3`** —
custom faces previously uploaded through the app. Not built-ins, and not named
`*.iwf`; `local_N` is the convention.

```
TX … 01 2A 00 08 … | 01 6C 6F 63 61 6C 5F 33 00…      (operate=01, "local_3")
RX … 01 2B 00 08 … | 00 01 6C 6F 63 61 6C 5F 33 00…   (status, operate_echo, name)
```

**The reply layout is `status` then `operate_echo`, not the reverse** —
`TooburV3DialPackets.isSuccess()` (`status == 1`) is reading the wrong byte for
this firmware; the set works. A follow-up `0x0006` still flags `local_1`
active, so the list's active marker is **stale / not authoritative** — do not
use it to verify a switch.

### 2d. The `D1` file-transfer channel — HANDSHAKE ONLY


Wire shapes from the official app's own upload,
`packetdumps/logcat/ui_watch_face_write_json.txt` (407 `D1` frames).

| Step | Frame | Live result on A200 |
|---|---|---|
| Announce | `D1 01 FF 2A D2 00 00 02 <name>` | `D1 01 00` — **accepted** |
| Start | `D1 05 0A` | `D1 05 00` — **accepted** |
| Data | `D1 02 00` + 134 B file bytes | `D1 02 09 00 …` — **refused** |
| Finish | `D1 03` | `D1 03 0B` — **aborted** |

The watch will *open* a file transfer and then rejects the payload. Tried with
both `hello.iwf.lz` and `local_4`; identical. Also tried 135- and 134-byte
payloads. In every case `D1 02` byte 2 = `0x09` and the write offset stays `0`.

### Framing, from the app capture

- Every data frame is exactly **137 B = the MTU**. The app sent 401 of them.
- Data-chunk ACKs are 20 B: `D1 02 00 <x> <y> <idx> 00 <offset u32 LE> 00…`.
  Offsets observed 1340, 2680, 4020, 5360, 6700 … stride **1340 = 10 × 134**,
  which is how the 134-byte payload size was derived.
- Nothing between `D1 05` and the first `D1 02` declares a total length, so the
  size is either in `D1 05 0A` (`0x0A` unexplained) or implicit in the announce
  preamble `FF 2A D2 00 00 02`.
- The app's announce name reads `…witch2.iwf.lz`; the *installed* dials are
  `local_N`, so the announced name is probably not what the dial is called.
- Bulk channel (`0x0AF1`) is **not** used; `D1` goes on `0x0AF6`, ACKed on `0x0AF7`.
- The payload is **not** raw file bytes — it is protobuf with embedded ASCII
  (filenames `iwf`, `…json`, `preview_2.bmp`, `image1.png` and JSON keys like
  `"type"`, `"bluetooth"`, `"custom"`). Decoding that schema from ~54 kB of
  samples is the main remaining job.

### Framing bug found and fixed (affects the whole repo)

The v3 length field is **`len(frame) - 3`** — every byte after the leading `0x33`
and before the 2-byte CRC. It is *not* `4 + len(payload)`, which is what the
existing probe scripts assumed. With the wrong value the watch returns **silence**,
which is what made `v3 0x07` and `v3 0x06` look unsupported in earlier sessions.

`scripts/toobur_gatt_dump.py:v3()` now reproduces the app's own frames byte for
byte:

```
0x07 app  33 DA AD DA AD 01 0B 00 07 00 50 01 82 A3
0x07 mine 33 DA AD DA AD 01 0B 00 07 00 50 01 82 A3   MATCH
0x1A mine 33 DA AD DA AD 01 0B 00 1A 00 02 00 5F F9   MATCH
```

Worth re-testing every previously-"silent" v3 command with this fixed.

### Screen geometry

`78 00 F0 00` in the app's `0x07` reply → plausibly **120 × 240**, with `85 00`
and a trailing `04` unexplained. Treat as unconfirmed. `IWFmake_ver1.py` targets
IDW19 at 240 × 284, a different SKU.

### Payoff if the upload is cracked

The trivial "silly" face needs no font or text-widget support: **one PNG with
something ridiculous drawn on it, used as the face `bkground`**. That is a
permanent, always-visible custom screen with no firmware risk.

Tooling: `scripts/toobur_dial.py` (list/switch dials), `scripts/toobur_bulk_probe.py`
(announce/start/data/finish).


## Route 3 — Realtek firmware ❌ BLE stubbed, hardware required

See [`custom_firmware.md`](custom_firmware.md). Short version: `01 01` acks
`err=0` but never reboots the watch into the Realtek bootloader, and no Realtek
DFU/OTA GATT service ever appears. There is **no firmware signature**, so the
obstacle is purely getting bytes onto the chip — which means UART/ISP with the
case open.

---

## Recommended order

1. **Today, zero risk:** route 1. It already works.
2. **Next, low risk:** finish route 2's data framing (declare the total length,
   match the app's exact filename, then reverse the protobuf from a *paired*
   capture — one where the app uploads a known face, so the plaintext `iwf.json`
   can be diffed against the bytes). Ends in a permanent custom face.
3. **Then, hardware:** UART/ISP for real firmware.

### Capture that would unblock route 2 fastest

One logcat run where the official app uploads a **tiny, known** face, capturing
both directions. With the plaintext `iwf.json` in hand, the protobuf becomes
solvable by diffing, and the framing falls out of the same trace.
