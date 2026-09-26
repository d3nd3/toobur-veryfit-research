# The `.iwf` watch-face format — research + A200 findings

What the `.iwf` container is, what the public reverse-engineering says, and what
I confirmed by extracting a real A200 face out of the official app's BLE upload.

**Headline:** the container magic, version field, entry count and the `RAW`
RGB565 image codec are all shared with the published spec. The **TOC layout is
not** — A200 uses a different record encoding, and its image entries appear to
be compressed. Also: the A200 screen is **120 × 240**.

---

## 1. Public tooling found

| Project | What it gives |
|---|---|
| **[VortexWatch/VeryEmulate](https://github.com/VortexWatch/VeryEmulate)** | The important one. `docs/FORMAT_SPEC.md` (15 kB reverse-engineering spec) plus `veryemulate/iwf_format.py`, `renderer.py`, and `tools/iwf_analyzer.py` — a working parser/renderer/emulator for `.iwf`. Derived from `f283.iwf` + strings in `idw26_ota_V1_00_14_20260211.fw`. |
| **[fbiego/watch-face-wearfit](https://github.com/fbiego/watch-face-wearfit)** | Different vendor (WearFit/Chronos) but the same *shape* of problem: `imager.jar` extracts a binary watchface to a folder of images, edits repack. Good reference for the extract→edit→repack workflow. |
| **[ArnCepTech/CloudDialSearcher](https://github.com/ArnCepTech/CloudDialSearcher)** | Talks to the IDO cloud dial API. Gives the endpoints and auth scheme (below). |
| **[coolsteel712/IWFmake](https://github.com/coolsteel712/IWFmake)** | Already in `research/repositories/IWFmake`. Targets IDW13/IDW19, builds `iwf.json` + `font.json`. |
| XDA: *"Need help making my own watch faces in .iwf format"* | Notably, other people are **stuck on the compression step** too. |

### IDO cloud dial API (from CloudDialSearcher)

```
listing : GET https://device.idoocloud.com/api/device/facestore/get/v4
detail  : GET https://device.idoocloud.com/api/device/face/v4/get
assets  : https://life-content.idoocloud.com/
headers : Authorization: Bearer <JWT>, appKey: 800a6444f9c0433c8e88741b6ddf1443
params  : deviceId, otaVersion, appFaceVersion, model, language, age, sex, height, weight, bmi, deviceToken
```

The checked-in token is **dead** — the API returns `status 201000`
("logged in on another device, please log in again"). A live token needs an IDO
account login, so this is a manual step, not something to work around. Once you
have one, this API is the cleanest source of a genuine `.iwf` for `deviceId=532`.

## 2. The format, per the published spec

`.iwf` is **not** ZIP/TAR. Flat proprietary container:

```
0x00  4  magic        "iwf\0"  (69 77 66 00)
0x04  2  version      u16 LE   (observed 1)
0x06  2  entry_count  u16 LE
0x08  …  TOC: entry_count × 40-byte records
         +0x00  32  name  (ASCII, NUL-padded)
         +0x20   4  offset (u32 LE, absolute)
         +0x24   4  size   (u32 LE)
      …    asset blobs, flat, at absolute offsets
```

`iwf.json` and `font.json` are **plain JSON**; images use a proprietary codec
despite `.png`/`.bmp` names.

### `RAW\0` image codec

```
0x00 4  magic "RAW\0"
0x04 2  width   u16 LE
0x06 2  height  u16 LE
0x08 1  pixel_format   (0x85 observed = RGB565-ish)
0x09 1  alpha_flag     0x66 = 4bpp alpha mask appended; 0x00 = opaque
0x0A 2  reserved       0x0000
0x0C 4  rgb_plane_size u32 LE (0 ⇒ compute width*height*2)
```

Then an **RGB565** plane, row-major, pixels **big-endian**
(`v = byte0<<8 | byte1`, `R=(v>>11)&0x1F`, `G=(v>>5)&0x3F`, `B=v&0x1F`) — note
the pixel plane is big-endian while the header/TOC are little-endian. Then,
if `alpha_flag != 0`, a **4bpp** alpha plane, two pixels per byte, low nibble
first, `(n*255)//15`.

### `iwf.json`

```json
{"version":1, "clouddialversion":3, "preview":"preview.png", "name":"...",
 "author":"...", "description":"IDW13", "deviceId":"IDW19",
 "bluetooth":false, "disturb":false, "battery":false,
 "compress":"LZ4", "environment":"Production",
 "bkground":"files0.png",
 "item":[{"widget":"custom","type":"date","x":..,"y":..,"w":..,"h":..,
          "fgcolor":"0xAARRGGBB","align":"left","font":"g282","fontnum":11}, …]}
```

`widget`/`type` select a firmware widget loader. The spec recovered these from
firmware strings: `watch_face_clock_load`, `watch_face_customtext_load`,
`watch_face_ring_load`, `watch_face_histogram_load`,
`watch_face_multimeter_load`, `watch_face_progressbar_load`,
`watch_face_gradient_load`, `watch_face_customanima_load`,
`watch_face_world_time_load`, `watch_face_weather_load`.

`font.json` declares glyph sets: `{"item":[{"name":"g282","bpp":16,"format":"png"}]}`.
Glyphs are **one file per character** (`g282_0`…`g282_10`, `week_en_mon`…), not a
packed atlas.

### The compression wrinkle

`iwf.json` declares `"compress":"LZ4"`, and the firmware contains a **FASTLZ**
decompressor (`module/compression/fastlz/fastlz_decompress_buff.c`). But the
spec's sample stored images *uncompressed* — decompression attempts with both
LZ4 and a hand-written FASTLZ level-1 decoder failed, while direct RGB565
decoding matched byte-exactly. Conclusion: `compress` is a **hint applied
per-entry**, not a container-wide guarantee.

## 3. What I confirmed on the A200

I extracted a genuine A200 face from the app's own upload
(`packetdumps/logcat/ui_watch_face_write_json.txt`): the 401 MTU-bound `D1 02`
frames concatenate into a **52,129-byte `.iwf`**, found by locating the `iwf\0`
magic. Saved as `packetdumps/extracted/upload.iwf`.

Ran the VeryEmulate analyzer against it:

```
Detected as IWF container: True
Magic: b'iwf\x00'   Version: 1   Entry count: 26
RAW proprietary image (IDW/VeryFit RGB565 codec): 17 hit(s)
Table ends at offset 1048 (matches first blob offset: False)   ← TOC does NOT reconcile
```

**Confirmed shared with the spec:** the `iwf\0` magic, `version=1`, an
entry-count field, and the `RAW\0` RGB565 image codec (17 signatures, with
`pixel_format = 0x85` throughout, same as the spec's sample).

**Not shared — A200's TOC differs.** 40-byte records do not reconcile; the
"entries" parse out as fragments of JSON, meaning the table and the JSON are
interleaved rather than laid out as a clean flat TOC. A200 looks like a
**TLV / key-value** stream rather than the IDW26 flat table.

### Screen is 120 × 240

Two independent confirmations:

1. v3 `0x07` device metadata: `… 42 61 6E 64 20 38 | 00 00 00 00 | 78 00 | F0 00 | 85 00 …`
   → `0x0078 = 120`, `0x00F0 = 240`.
2. A `RAW\0` header in the extracted file at offset 1271 reads **`120 x 240`** —
   the full-screen background.

(IWFmake's 240 × 284 is IDW19; wrong SKU for A200.)

### Entry names and JSON keys actually present

Names, in file order: `iwf.json`, `font.json`, `image1.png`, `preview_2.bmp`,
`battery_4bit.bmp`, `num_hour_min_5`, `steps`.

JSON keys, in file order — a superset of the spec's IDW26 set:

```
version, preview, name, author, description, bluetooth, disturb, battery,
background, item[], widget, type, x, y, w, h, fgcolor, bgcolor, align,
center, num_hour_min, sleep, icon, pro, ssbar, steps, format
```

Recoverable fragments include `"version": 2,`, `"bluetooth":true`,
`fgcol:"0xFF70F9F0"`, `"type" :"bluetooth"`, `num_hour_min_5`,
`num_hour_mi…`, `battery_4bit.bmp`, `preview_2.bmp`, `b9ground` (`background`).

Note `version: 2` here vs `version: 1` in the spec's sample — A200 faces are a
**newer schema generation**.

### A200 image entries are compressed

Glyph headers decode as `60 x 80` and `10 x 18` with `rgb_size` exactly
`w*h*2` (9600 and 360), i.e. plausible. But consecutive `RAW` signatures are
only ~900–1100 bytes apart, while a 60×80 RGB565 plane alone is 9600 bytes.
So the stored blob is far smaller than the decoded image ⇒ **entries are
compressed** and the header describes the *decompressed* size. This is the
`compress` / FASTLZ path, and it is the piece that stalls everyone, myself
included.

## 4. What this means for putting a silly face on the watch

The bones are now known: a 120 × 240 `RAW` RGB565 background is all a face
strictly needs — draw something ridiculous as a 120×240 RGB565 image, wrap it
with `iwf.json` (`bkground` + empty `item[]`), and upload. Three things still
block that:

1. **A200's TLV record encoding** — needs one clean sample to derive. Best
   source: a live IDO cloud token, or export a face from the app on the phone.
2. **The per-entry compression** — needs the exact algorithm/level (FASTLZ
   level 1 vs LZ4) confirmed on an A200 entry.
3. **The `D1 02` framing** — the 7-byte header is still unexplained, and the
   watch rejects data with `st=09` and a write offset frozen at 0, which smells
   like a missing total-length declaration.

Item 1 is the cheapest to clear and unblocks the other two, because a real
A200 `.iwf` is directly analysable by the VeryEmulate tooling.

## 5. Artifacts and tooling

- `packetdumps/extracted/upload.iwf` — real 52,129-byte A200 face, extracted
  from the app capture. (Still the vendor's copyrighted face; for local analysis.)
- `scripts/toobur_dial.py` — list / switch dials (v3 `06` / `08`), works
- `scripts/toobur_bulk_probe.py` — `D1` announce/start/data/finish
- [`docs/screen_payloads.md`](screen_payloads.md) — the text-on-screen route
  that works today, and the `D1` findings in context
