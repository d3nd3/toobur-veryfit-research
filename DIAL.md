# DIAL — watch faces on the Toobur A200

Everything known about dials / watch faces on this watch: how to list them, how
to switch them (works, confirmed on-device), how new ones get uploaded
(handshake only), and what the `.iwf` container actually is.

Live device: `F9:24:12:2E:0C:32` "Band 8", fw 17, MTU 137, screen **120 × 240**.

Related: [`docs/iwf_format.md`](docs/iwf_format.md) (container deep-dive),
[`docs/screen_payloads.md`](docs/screen_payloads.md) (all screen-payload routes),
[`A200-PROTOCOL.md`](A200-PROTOCOL.md) (canonical wire map).

---

## TL;DR

| Operation | v3 cmd | Status |
|---|---|---|
| List dials | `0x06` | ✅ works live |
| **Switch dial** | `0x08` | ✅ **works — face visibly changed** |
| **Sideload a whole new dial** | `D1 01/05/02/03` | ✅ **WORKS — full upload + install verified** |

**Switching dials is solved, and so is uploading a brand-new one.** A complete
`.iwf` was pushed to the watch over BLE, the watch accepted it (`D1 03 00`), and
the new dial appeared in the list and was activated. The last unknown — the
`D1 03` check code — is solved: it is a plain **additive byte sum**, not CRC32.

## 0. Sideloading a new dial — SOLVED ✅

This is the headline. `scripts/toobur_d1_replay.py` performs a complete upload.

```
-- conn param 0   03 35 00 00 00 00 00 00 00 00 00 00     (VBUS 157 — REQUIRED)
-- conn param 1   03 35 01 00 00 00 00 00 00 00 00 00 00
-- MTU            02 F0
-- announce       D1 01 FF <size:u32 LE> <compression:u8> <name>
                  RX  D1 01 00
-- start          D1 05 0A                              (batch_size = 10)
                  RX  D1 05 00
-- data           D1 02 00 <≤134 bytes>   × N
                  RX  D1 02 <status:u8> <running_sum:u32 LE> <cum_bytes:u32 LE>
-- finish         D1 03 <check:u32 LE>
                  RX  D1 03 00                            ← SUCCESS
```

Verified run:

```
RX D1 01 00  OK
RX D1 05 00
40 acks, 40 successful, last offset 53600
RX D1 03 00  -> SUCCESS
dial list: local_1, local_2, local_3, witch2.iwf      ← new dial present
```

### The check code is an additive sum, not CRC32

`D1 03 <u32 LE>` = **sum of every payload byte**, little-endian. Proven against the
official capture:

```
announced size      53,802 B
sum(payload)     =  5,008,679  = 0x004C6D27
D1 03 in capture  =  27 6D 4C 00   (LE u32 = 0x004C6D27)   ← exact match
```

The `running_sum` in each `D1 02` ack is the *same* sum, cumulative — verified on
16/40 acks (the rest are duplicate log lines):

```
run=101863  sum(payload[:1340])=101863   OK
run=213501  sum(payload[:2680])=213501   OK
```

This is why plain `zlib.crc32` fails. The vendor's `libVeryFitMulti.so` does
export `crc32`/`crc32_z`/`get_crc_table` (zlib's, table starts `0x77073096`) and a
`get_file_crc` — but the D1 end-of-transfer check is a plain additive sum. zlib
CRC32 *is* used elsewhere, for the v3 `0x33` frame CRC16 and `get_file_crc` on
other paths. Independent project `coolsteel712/VeryLoad` hit this same wall and
shipped a documented **CRC32 placeholder**; having the actual payload bytes is
what let it be resolved here.

### Payload framing — the "5-byte header" was a red herring

`D1 02` frames are `D1 02 00` (**3** bytes) + file payload. The remaining bytes are
**file content**, not a header. So the file starts with 5 bytes before `iwf\0`:

```
payload[0:5]  00 00 01 8D 27
payload[5:]   69 77 66 00 01 00 1A 00 …      ← "iwf\0", version 1, file_count 26
```

- 134-byte chunks × 401 frames + one 68-byte tail = **53,802** = the announced size.
- `D1 05 0A` batch_size=10 → the watch acks every 10 frames, and
  `cum_bytes` advances by 10 × 134 = **1340** per ack. Matches the capture exactly.
- Two 4-byte `D1 02 00 00` / `D1 02 00 EE` frames appear in the log but are **not**
  file data. Counting them breaks the check code by 238.

### Prerequisites that are easy to miss

1. **The connect prelude** (see §1) or the watch ignores everything.
2. **The `03 35` conn-param preamble.** Without it the watch crawls and the
   transfer stalls around frame 110.
3. **Write-with-response, paced.** Blasting frames overruns the watch's RX buffer
   and it drops the link. `--gap 0.006` works; a per-frame GLib main loop is far
   too slow and also kills the link. `bulk_send()` does it in one loop.
4. **Retry the whole sequence on disconnect** — BLE drops somewhere around
   frame 370/402 on a long transfer. `--retries N` handles it.

### Tooling

```bash
python3 scripts/toobur_d1_replay.py --dry-run          # show framing + check code
python3 scripts/toobur_d1_replay.py --list-after       # full upload, then list dials
python3 scripts/toobur_d1_replay.py --retries 5 --gap 0.006
```

## 1. Prerequisites — the connect prelude


The watch **ignores every v3 command** until the VeryFit connect prelude has run.
Without it you get silence and it looks like a dead device:

```
02 01        GET device info
02 02        GET func table
02 07        GET func ex
02 F0        GET MTU
33 DA AD DA AD 01 0B 00 1A 00 02 00 5F F9    v3 func table
```

`scripts/toobur_gatt_dump.py` does this for you (`--prelude`).

### Framing bug that breaks every v3 command

The v3 length field is **`len(frame) - 3`** — every byte after the leading `0x33`
and before the 2-byte CRC. It is **not** `4 + len(payload)`.

```
33 DA AD DA AD 01 [len LE] [cmd LE] [seq LE] [payload…] [CRC16 LE]
```

A wrong value gets **silence**, not an error. CRC16-CCITT (poly `0x1021`, init
`0xFFFF`) over bytes `[1, len-2]`. `scripts/toobur_gatt_dump.py:v3()` reproduces
the official app's frames byte for byte:

```
0x07 app  33 DA AD DA AD 01 0B 00 07 00 50 01 82 A3
0x07 mine 33 DA AD DA AD 01 0B 00 07 00 50 01 82 A3   MATCH
0x1A mine 33 DA AD DA AD 01 0B 00 1A 00 02 00 5F F9   MATCH
```

Any v3 command previously marked "silent" in this repo is worth re-testing.

## 2. List dials — v3 `0x06` ✅

`TooburV3DialPackets.buildGetListRequest` → 14-byte frame, lenField `0x000B`.

```
TX 33 DA AD DA AD 01 0B 00 06 00 00 02 EA EB
RX 33 DA AD DA AD 01 36 00 06 00 00 02
   01 03 00 01 00 1C
   01 01 07 00 00 00 "local_1"
   01    07 00 00 00 "local_2"
   01    07 00 00 00 "local_3"
   18 0E
```

Vendor schema for this reply
(`Flutter_GitBook/en/doc/BaseProtocolEvtExecDoc/IDOV3Evt/IDOV3GetDialList.html`):

```json
{"version":0, "available_count":0, "file_max_size":140,
 "item":[{"file_name":"w256.iwf"}]}
```

| Offset | Field | Our value |
|---|---|---|
| 0 | `version` | `1` |
| 1 | `available_count` | `3` ✅ matches 3 entries |
| 2–5 | `file_max_size` (u32 LE) | `256` — unit unconfirmed (KB? a different field?) |
| 6… | `item[]` | see below |

Item encoding (matches `TooburV3DialPackets.parseListFrame`):

```
[ dial_type:1 ] [ 01 if active ] [ name_len:1 ] [ 00 00 00 ] [ name ]
```

`dial_type` is `1` = Colour (`IDOV3NoticeDialChange`: `0` invalid, `1` colour).

**This watch's dials are `local_1`, `local_2`, `local_3`** — custom faces
uploaded through the app previously. Note they are *not* named `*.iwf`, unlike
the vendor doc's `w256.iwf` examples. `local_N` is the A200 convention.

### ⚠️ The "active" marker is not trustworthy

After switching to `local_3` and then `local_2`, a fresh `0x06` **still reported
`local_1` as active** — yet the watch visibly displayed the new face both times.
Treat the active flag as stale; it is not a valid way to verify a switch. Only
the screen is.

## 3. Switch dial — v3 `0x08` ✅ CONFIRMED

`TooburV3DialPackets.buildSetDialRequest` → lenField `0x002A`, 45-byte frame,
31-byte payload: `operate` + ASCII filename, zero-padded.

```
TX 33 DA AD DA AD 01 2A 00 08 00 00 03
   01 "local_3" 00×23
   87 5B
RX 33 DA AD DA AD 01 2B 00 08 00 00 03
   00 01 "local_3" 00×23
   CD 15
```

**→ The watch face visibly changed to the red/green dial. This works.**

### Reply layout — and a Gadgetbridge bug

Vendor schema (`IDOV3SetDial.html`):

```json
{"err_code":0, "operate":0, "file_name":"w256.iwf", "file_count":0}
```

So the payload is **`err_code` first, then `operate`, then `file_name`, then
`file_count`**. Our reply `00 01 "local_3" 00…` is:

| Byte | Field | Value |
|---|---|---|
| 0 | `err_code` | `0` = **success** |
| 1 | `operate` | `1` (echo of what we sent) |
| 2… | `file_name` | `"local_3"` |

**Bug:** `TooburV3DialPackets.isSuccess()` returns `status == 1`, reading
`payload[1]` — which is the `operate` echo, not the status. It reports failure
on every successful set. Success is **`err_code == 0`**, i.e. `payload[0] == 0`.
Worth fixing in the Gadgetbridge tree.

`operate` values: `0` query, `1` set. `operate=3` requests a dynamic size change
for a to-be-deleted filename (gated on the func-table bit
`v3WatchDailSetAddSize`; defaults to `1` if absent).

## 4. Upload a new dial — see §0 (SOLVED) ✅

Retained for reference: the earlier handshake-only state and the framing notes that led to §0.

### Historical: handshake only ⚠️

Wire shapes from the official app's own upload:
`packetdumps/logcat/ui_watch_face_write_json.txt` (407 `D1` frames).

| Step | Frame | Live result |
|---|---|---|
| Announce | `D1 01 FF <size:u32 LE> <compression> <name>` | `D1 01 00` — accepted |
| Start | `D1 05 0A` | `D1 05 00` — accepted |
| Data | `D1 02 00` + ≤134 B | `D1 02 09 …` if the size/check are wrong; `00` + advancing offset when right |
| Finish | `D1 03 <sum:u32 LE>` | `D1 03 0B` if the sum is wrong; `D1 03 00` when correct |

The watch *will open* a file transfer, then rejects the payload. Tried with
`hello.iwf.lz` and `local_4`; 135- and 134-byte payloads. Identical every time.

### Framing, from the app capture

- Data frames are exactly **137 B = the MTU**; the app sent 401 of them.
- **Header is 7 bytes** (`D1 02` + 5), which varies per frame and is still
  unexplained. Note the file's `iwf\0` magic begins one byte *after* a 7-byte
  header, i.e. there are 8 bytes before the magic in frame 0.
- Data ACKs are 20 B: `D1 02 00 <x> <y> <idx> 00 <offset u32 LE> 00…`.
  Offsets run 1340, 2680, 4020, 5360, 6700 … stride **1340 = 10 × 134**, which
  is how the 134-byte payload guess was derived.
- Nothing between `D1 05` and the first `D1 02` declares a total length. The size
  is either in `D1 05 0A` (`0x0A` unexplained) or implicit in the announce
  preamble `FF 2A D2 00 00 02`.
- The app's announce name reads `…witch2.iwf.lz`, but installed dials are
  `local_N` — so the announced name is probably not the dial's name.
- `D1` uses the **normal** chars `0x0AF6` / `0x0AF7`, **not** the bulk pair.

`D1 02` byte 2 = `0x09` with the write offset frozen at `0` looks like a missing
total-length declaration rather than bad content.

**`st=09` is not an error code we can interpret yet** — the app's successful
transfers show `0x00` with an advancing offset, so compare against that.

## 5. The `.iwf` container

Authoritative source is the vendor's own compiler, `coolsteel712/VeryLoad` →
`CloudDialMake/` (fetch `make_watch_face.cpp` and `watch_face_rw_head.h`).

```c
// watch_face_rw_head.h
#define WATCH_FACE_RW_FILE_MAGIC "iwf"
#define WATCH_FACE_RW_FILE_NAME_MAX_LENGTH 30
#define WATCH_FACE_RW_FILE_LIST_MAX_NUMBER  10

typedef struct watch_face_file {
    char     name[30];
    uint32_t offset;
    uint32_t length;
} watch_face_file_t;                 // 38 bytes per TOC record

typedef struct watch_face_file_head {
    char     magic[4];                // "iwf" + NUL
    uint16_t version;                 // 1
    uint16_t file_count;
} watch_face_file_head_t;            // 8 bytes
```

**TOC records are 38 bytes, not 40.** That is why the published VeryEmulate spec
(which says 40) fails to reconcile on A200 — and this is confirmed by the vendor
header, not guessed.

### What the A200 file actually contains

Extracted: `packetdumps/extracted/witch2.iwf.lz` (53,802 B, the exact bytes sent)
and `witch2.iwf` (53,797 B, from the `iwf\0` magic onward).

| Property | Value |
|---|---|
| 5-byte prefix | `00 00 01 8D 27` before `iwf\0` — purpose unknown |
| Header | `iwf\0`, version 1, `file_count` 26 ✅ |
| Screen | **120 × 240** — the background PNG in the CDN zip is exactly 120×240 |
| `iwf.json` | plain JSON, `"version": 2` |
| Images | **no PNG signatures in the container** — assets are converted bitmaps |

`iwf.json` (verbatim from the CDN zip) confirms the schema:

```json
{ "version": 2, "preview": "preview_2.bmp", "name": "witch2", "author": "yxr",
  "bluetooth": true, "disturb": true, "battery": true,
  "bkground": "image1.png",
  "item": [ { "widget":"custom","type":"hour","x":0,"y":39,"w":120,"h":80,
              "fgcolor":"0xFF70F9F0","font":"num_hour_min","fontnum":10 }, … ] }
```

`font.json` declares glyph sets (`num_hour_min`, `num_steps`, `bpp:16`).

**Resolution warning:** community tables map "TOOBUR → 240×284" (that is IDW19,
the Milouz, which is what IWFmake targets). This watch measures **120×240** by two
independent routes — the v3 `0x07` reply and the actual background bitmap. Do not
trust the table.

### The TOC is a custom TLV, not a flat table

A flat 38-byte-record parse yields JSON fragments as "names"
(`"on": 2,`, `witch2`, `author`, `yxr`, `bluetooth":true`, `image1.png`, `fgcol`,
`0xFF70F9F0`, `num_…`, `steps`) with impossible offsets. The container
interleaves a tag/length/value encoding with the JSON, so the on-wire TOC is not
the same layout `makeIwfFile()` writes to disk. **Not yet fully reversed** — but it
no longer blocks uploads, because payloads can be replayed byte-for-byte.

## 6. Getting a *silly* face onto it — remaining work

The transport is done, so this is now purely a content problem. Three routes:

1. **Build the vendor compiler.** `CloudDialMake` has `makeIwfFile()`, plus
   `fastlz.c`, `lz4.c`, `bitmap_tool.c`, `png2bmp.c` and jsoncpp. Compile it, point
   it at a folder of assets, emit a container, upload. This is the clean route and
   gives arbitrary control.
2. **Patch the container in place.** The background is the largest asset, so a
   same-length replacement of its bitmap plus a corrected `D1 03` sum would work
   today. Needs the converted-bitmap layout from `bitmap_tool.c`.
3. **Text on screen now, no face needed.** `scripts/toobur_hello_world.py` works.

## 6b. Source material and tooling

| Resource | Value |
|---|---|
| CDN dial zip | `https://life-content.idoocloud.com/otaFace/<uuid>.zip` — loose `iwf.json` + `font.json` + PNGs |
| `coolsteel712/VeryLoad` | the BLE sideloader; `docs/PROTOCOL_SPEC.md` documents `D1` and v3 framing |
| `CloudDialMake/` in that repo | the vendor compiler + `watch_face_rw_head.h` (authoritative container) |
| `VortexWatch/VeryEmulate` | published spec + analyzer; 40-byte TOC is wrong for A200, codec/JSON guidance still useful |
| `ArnCepTech/CloudDialSearcher` | cloud dial API + auth scheme |

## 7. Tooling

| Script | Purpose |
|---|---|
| [`scripts/toobur_dial.py`](scripts/toobur_dial.py) | List dials (`06`), switch (`08`), `--silly` random pick, `--cycle N` |
| [`scripts/toobur_bulk_probe.py`](scripts/toobur_bulk_probe.py) | Drive `D1 01/05/02/03` + dial list |
| [`scripts/toobur_d1_replay.py`](scripts/toobur_d1_replay.py) | **full `D1` sideload** — the working uploader |
| [`scripts/toobur_d1_sweep.py`](scripts/toobur_d1_sweep.py) | Sweep `D1` opcodes for a read path |
| [`scripts/toobur_gatt_dump.py`](scripts/toobur_gatt_dump.py) | Shared: connect/prelude/`v3()`/CRC |
| [`scripts/toobur_hello_world.py`](scripts/toobur_hello_world.py) | Arbitrary text on screen via `MSG 05 03` (works) |

```bash
python3 scripts/toobur_dial.py                    # what's on the watch
python3 scripts/toobur_dial.py --set local_2      # switch (works)
python3 scripts/toobur_dial.py --silly            # random other dial
python3 scripts/toobur_dial.py --cycle 3          # walk all three
```

## 8. Open questions

**Solved since first draft:**

- ~~`D1 05 0A` meaning~~ → **batch_size = 10** raw packets per ack.
- ~~`D1 02` 5-byte header~~ → **not a header**; it is file content. Frame is
  `D1 02 00` + payload.
- ~~`D1 03` check code~~ → **additive byte sum**, u32 LE. Proven exactly.
- ~~Does the watch accept a new dial?~~ → **yes**, verified in the dial list.

**Still open:**

- The 5-byte prefix `00 00 01 8D 27` before `iwf\0` — what is it?
- Compression type byte: the capture uses `0x02` yet the payload is *not*
  LZ4/FASTLZ-compressed (plaintext JSON and readable bitmaps inside). So `0x02`
  apparently does not mean "compressed", or A200 ignores it. CloudDialMake ships
  both `fastlz.c` and `lz4.c`; the VeryLoad spec notes a `d10200` chunk header for
  `.iwf.lz`. Untested whether A200 accepts a genuinely compressed payload.
- On-wire TOC encoding (differs from the 38-byte on-disk layout).
- Converted-bitmap asset layout (`bitmap_tool.c` / `png2bmp.c`) — needed to
  replace the background without recompiling.
- Does any `D1` opcode *read* a file back? A sweep of `00`–`10` was started but
  the link dropped mid-run, so that result is **void — needs redoing**.
- `file_max_size = 256` in the `0x06` header — bytes, KB, or a different field?
  Our successful payload was 53,802 B, so 256 is clearly not a byte limit.
- Does `IDOV3NoticeDialChange` (watch→phone) fire when the dial list changes?
- `v3WatchDailSetAddSize` func-table bit — present on A200?
