# V3 continuous HR command — research notes

## Naming: `hr_mode_set` and related symbols

The literal string **`hr_mode_set`** does **not** appear in this repo’s logcats. It is a plausible **native / protocol** name (C/Java) for “set HR mode over v3.” In decompiled VeryFit / `libido` / `protocol_v3*.c` sources, grep:

- **`hr_mode_set`**
- **`func_v3_set_hr_mode`**
- **`V3_SET_HR_MODE`**

They should tie to the same pipeline as:

| Layer | Name / id |
|-------|-----------|
| Logcat | **`5010`** = **`VBUS_EVT_FUNC_V3_SET_HR_MODE`** |
| JNI | **`Java_com_veryfit_multi_nativeprotocol_Protocol_WriteJsonData`** → evt **5010** |
| Wire | **v3 cmd `0x0009`**, header bytes **`01 17 00 09 00`** (length `0x17`, cmd `0x09`) |
| HTML UI | **`v3_set_hr_mode`**, **`func_v3_set_hr_mode`** ([`confirmed-only.html`](../htmlapp/confirmed-only.html)) |

So: **`hr_mode_set` ≈ V3_SET_HR_MODE ≈ v3 packet cmd 0x09** for HR (and reused for stress / drink / walk / woman-health variants with different inner payloads).

---

VeryFit / IDO **continuous heart-rate on** uses **v3 cmd `0x0009`** with a **two-write sequence**. Same VBUS event is reused for other features (stress, walk-around, drink reminder, etc.) with **one** v3 frame each; HR continuous is special.

## VBUS / SDK

| Item | Value |
|------|--------|
| Logcat event | `5010` = **`VBUS_EVT_FUNC_V3_SET_HR_MODE`** |
| JNI | `Java_com_veryfit_multi_nativeprotocol_Protocol_WriteJsonData` |
| Wire | GATT write **0x0AF6**, v3 packet prefix `33 DA AD DA AD` |
| v3 **cmd** (bytes 8–9 LE) | **`09 00`** → `0x0009` |
| v3 **length** (bytes 6–7 LE) | **`17 00`** → `0x0017` (23) bytes after the 2-byte **nseq** in the length accounting used by the stack |

IDO GitBook (high level, no raw bytes): **Set / Get v3 heart rate mode** / **`IDOSetV3HeartRateModeBluetoothModel`** — fields include `modeType`, `measurementInterval`, time range, `notifyFlag`, high/low HR alerts. **Get**: [IDOGetV3HrFunction](https://idoosmart.github.io/IDOGitBook/en/get/IDOGetV3HrFunction.html). The SDK model clearly matches **evt 5010 / v3 cmd `0x09`**, but the wire dumps only expose part of the model directly.

### GitBook model vs wire (`0x09`) — current match level

| SDK field | Dump evidence | Confidence | Notes |
|-----------|---------------|------------|-------|
| `modeType` | ON/OFF differ in one mode-ish byte (`99` vs `AA`) and in startup zero-payload variants | Medium | Not sent as literal enum `0..6`; firmware likely uses an internal encoding / subtype. |
| `updateTime` | pkt1 bytes `D8 AD AC 69` (ON) vs `BA AD AC 69` (OFF) differ by ~30 s | High | Strongly looks like a LE timestamp / update-time field. |
| `isHasTimeRange` | pkt2 contains `01 00 00` before `17 3B` | Medium | Likely “has time range” plus padding / flags. |
| `startHour`, `startMinute` | pkt2 prefix is all zeros before `17 3B` | Medium | Best fit is start=`00:00` in the captured “all day” config. |
| `endHour`, `endMinute` | pkt2 contains `17 3B` | High | Cleanly decodes to `23:59`. |
| `measurementInterval` | pkt1 contains `2C 01` | High | `300` s on wire; HTML tool patches this word for experiments. |
| `notifyFlag` | no clear field in captured `0x09` HR packets | Low | Present in SDK model, not identified on wire here. |
| `highHeartMode`, `lowHeartMode`, `highHeartValue`, `lowHeartValue` | no clear field in captured `0x09` HR packets | Low | May be omitted on this watch, encoded elsewhere, or only used in another 5010 shape. |
| `getSecondMode`, `hrModeTypes` | no direct wire match | Low | Probably returned logically to SDK, not present in these set-style packets. |

## Continuous ON — two TX packets (A200 capture)

Source: [`packetdumps/logcat/set_hr_cont_state_on.txt`](../packetdumps/logcat/set_hr_cont_state_on.txt).

### Packet 1 — nseq `0x0117`

```
33 DA AD DA AD 01 17 00 09 00  17 01  D8 AD AC 69  99  00 00 00 00 00  2C 01  [CRC LE]
```

| Offset (after `09 00`) | Bytes | Role (inferred) |
|------------------------|-------|------------------|
| 0–1 | `17 01` | **nseq** LE = `0x0117` |
| 2–5 | `D8 AD AC 69` | Likely **`updateTime`** / timestamp-like LE word rather than fixed magic; OFF capture uses `BA AD AC 69` ~30 s earlier |
| 6 | `99` | Mode/subtype byte (firmware-specific; not raw GitBook `modeType`) |
| 7–11 | `00`×5 | Padding / reserved |
| 12–13 | `2C 01` | **LE u16 = 300** — matches SDK **measurementInterval** in seconds (5 min in this capture). `toobur-hr-csv.html` patches this for “custom interval”. |
| 14–15 | CRC-16-CCITT-FALSE | Over bytes from `DA` … last payload byte |

### Packet 2 — nseq `0x0118` (~150 ms later)

```
33 DA AD DA AD 01 17 00 09 00  18 01  00 00 00 00 00  01 00 00  17 3B  00 00  [CRC LE]
```

| Bytes | Role (inferred) |
|-------|------------------|
| `18 01` | **nseq** = `0x0118` |
| `00 00 00 00 00` | Best fit: start time range `00:00` plus one extra zero / padding byte |
| `01 00 00` | Likely **has_time_range** and/or flags |
| `17 3B` | **23:59** (end of day) — strong match for `endHour` / `endMinute` |
| `00 00` | Padding |

Logcat: first packet queued as **cmd id=0x9 nseq=0x117**; second queued with **“cmd is not reply”** — stack treats this as **one logical operation** completed when **nseq 0x118** finishes (`send_end`).

## RX replies (same capture)

Two **33-byte** notifications, **cmd 0x09**, inner length **`1F 00`** (31):

- **nseq 0x117** reply echoes `99`, `2C 01`, ends with `04 00 00 00` before CRC — `04` is stable across all seen replies, but it does **not** track ON/OFF or literal GitBook `modeType`; treat it as a firmware reply/status code for now.
- **nseq 0x118** reply similar shape.

## Continuous OFF

[`set_hr_cont_state_off.txt`](../packetdumps/logcat/set_hr_cont_state_off.txt): often **two** frames as well (`14 01` … then `15 01` …). Single-button “off” in HTML may send only first; full OFF sequence in dump uses seq **0x114/0x115** family — compare with your firmware.

## Other uses of evt 5010 / v3 `09` (single packet)

Same **V3_SET_HR_MODE** event, **different** inner payload (no `D8 AD AC 69` block):

| Capture | nseq (typ.) | Notes |
|---------|-------------|--------|
| `set_stress_cont_on.txt` | `1C 01` | Stress continuous |
| `set_walkaround_cont_on_*.txt` | `22 01` | Walk reminder |
| `set_drinking_cont_*.txt` | `1E` / `1F` | Drink reminder |
| `set_woman_health_remind_*.txt` | `31 01` | Woman health |
| `app_fresh_launch.txt` | `03`, `04`, `09` | Early config; shorter/zero tail variants |

Shared tail pattern in many singles: `… 01 00 00 17 3B 00 00` + CRC.

## `app_fresh_launch.txt` — startup/default config shapes

Fresh app launch sends additional **evt 5010 / cmd `0x09`** packets:

```text
33 ... 09 00 03 00 00 00 00 00 00 01 00 00 17 3B 00 00 ...
33 ... 09 00 04 00 00 00 00 00 00 01 00 00 17 3B 00 00 ...
33 ... 09 00 09 00 00 00 00 00 00 00 00 00 00 00 00 00 ...
```

These are important because they show:

1. **Same VBUS event / command**, but multiple payload shapes under the SDK model.
2. The **`03` / `04`** startup shapes carry the same **time-range tail** (`01 00 00 17 3B 00 00`) without the timestamp-like word or `2C 01` interval.
3. The **`09`** startup/sync-config shape is almost all zeros and still gets a normal `0x09` reply ending in `04 00 00 00`.

Best interpretation: GitBook’s `IDOSetV3HeartRateModeBluetoothModel` is the **logical model**, while firmware uses **several compact on-wire encodings** for:

- startup / default sync config,
- continuous ON,
- continuous OFF,
- perhaps other HR-mode subtypes.

## Related (not the same command)

- **GET `02 08`**: HR / health state readback (often 4× burst after **SET `03 45`** health toggles).
- **SET `03 25` / `03 24`**: Legacy angelfit HR mode / zone thresholds.
- **v3 health sync type 3**: Historical HR day sync (**cmd `0x04`**, data type 3) — different from **setting** continuous mode.

## Empirical log (captured continuous ON, repeated)

Same TX twice (preset **v3 continuous ON**, not custom):

- **RX** after pkt1 (nseq `0x117`): `… 2c 01 … 04 …` CRC `f9 99`
- **RX** after pkt2 (nseq `0x118`): `… 2c 01 … 04 …` CRC `73 d6`

Echoed interval **always `2C 01` = 300 s** because TX always sends 300. **`04`** stable as mode byte. CRC differs per nseq. Re-sending the same pair reproduces the same RX — expected.

To see **60** or **600** in the echo, TX packet 1 must send **`3C 00`** or **`58 02`** (LE) in place of **`2C 01`** (**Custom interval** in `toobur-hr-csv.html`).

### Empirical: custom TX 60 / 300 / 600 s (pkt1 patched)

**TX** pkt1 correctly carries **LE interval** at bytes 22–23 (`3c 00`, `2c 01`, `58 02`).

**RX** (nseq `0x117` / `0x118`) **always** contained **`2c 01`** at the same offset and **`04`** mode byte — **independent of TX interval**.

**Interpretation:**

1. The reply field is **not** a simple echo of pkt1’s interval word on this firmware; it may reflect a **fixed internal default** (300 s), last VeryFit sync, or another config slot.
2. Patching pkt1 alone may **not** change continuous HR measurement period; pkt2 or a **full JSON-shaped** 5010 payload (as the native app builds) might be required.
3. Alternatively **`2c 01` in RX** means something other than “current measurement interval” (e.g. zone threshold in same byte layout).

## Open questions

1. Exact **bitfield** meaning of bytes around `01 00 00` in packet 2.
2. Whether **`99`** is fixed for HR or varies by firmware.
3. Whether second packet **`17 3B`** must track first packet interval for all devices.
4. **Off** sequence: full 2-pkt vs 1-pkt per firmware.

## References in this repo

- [`TOOBUR.md`](../TOOBUR.md) — VBUS 5010, IDO SDK cross-ref.
- [`htmlapp/confirmed-only.html`](../htmlapp/confirmed-only.html) — TX buttons + v3 HR form.
- [`htmlapp/toobur-hr-csv.html`](../htmlapp/toobur-hr-csv.html) — continuous ON + interval patch.
