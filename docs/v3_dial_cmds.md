# v3 Dial Commands (`cmd 0x06` / `cmd 0x08`)

This note documents what we currently infer about the watch-face ("dial") v3 commands from live logcat captures and GitBook pages.

## TL;DR mapping

- `evt:5006` -> v3 `cmd id=0x06` -> **get dial list (new)** path
- `evt:5008` -> v3 `cmd id=0x08` -> **set/query dial** path (operate + file_name)

Confidence:
- `0x06 == get list`: **high**
- `0x08 == set/query dial`: **high**
- "notice dial change" and "set dial sort": likely same dial subsystem, maybe different `operate` values under `0x08`: **medium**

## Evidence from logs

## 1) `evt:5006` uses `cmd 0x06` and returns list-like names

From `packetdumps/logcat/ui_select_watch_face.txt`:

- App sends `evt:5006(5006)`.
- Queue logs: `v3 protocol add queue cmd id=0x6`.
- TX:
  - `33 DA AD DA AD 01 0B 00 06 00 4E 01 ...`
- RX payload includes watch entries / names:
  - `local_1`, `local_2`, `local_3` (and in other captures `witch2.iwf`).

This aligns with GitBook `IDOV3GetDailLIstNew.md` ("V3 get watch list new interface").

## 2) `evt:5008` uses `cmd 0x08` and carries set/query dial payload

From `packetdumps/logcat/ui_watch_face_write_json.txt`:

- App sends `evt:5008(5008)`.
- Queue logs: `v3 protocol add queue cmd id=0x8`.
- TX #1:
  - `33 DA AD DA AD 01 2A 00 08 00 52 01 00 00 ...`
  - Payload after `nseq` is mostly zero.
- TX #2:
  - `33 DA AD DA AD 01 2A 00 08 00 53 01 01 77 69 74 63 68 32 2E 69 77 66 ...`
  - Contains ASCII `witch2.iwf`.
- RX echoes same `nseq` and returns `witch2.iwf` in response payload.

This aligns with GitBook `IDOV3SetDial.md`:
- `operate` (`0=query current`, `1=set`, `2=delete`, `3=dynamic allocate`)
- `file_name` (char[])
- optional size-related field depending on function table.

## Wire shape observations

Common v3 frame prefix:

- Header: `33 DA AD DA AD`
- Version: `01`
- Length: little-endian bytes `[6..7]`
- Command: little-endian bytes `[8..9]` (`06 00` or `08 00`)
- Sequence: little-endian bytes `[10..11]`

For `cmd 0x08` in these captures:

- Total frame seen: 45 bytes (`len=0x2A` payload+overhead convention used by this firmware)
- Request payload region after `nseq` appears to be fixed-width (32 bytes in observed frames):
  - byte 0: likely `operate`
  - following bytes: likely `file_name` C-string area / zero-padded

For `cmd 0x06` responses:

- Variable payload containing list metadata + watch names (ASCII fragments visible in plain hex).

## Candidate API mapping table

- `IDOV3GetDailLIstNew` / `GetailListNew` -> `cmd 0x06` (via `evt:5006`) **[high]**
- `IDOV3SetDial` -> `cmd 0x08` (via `evt:5008`) **[high]**
- `IDOV3GetGetDialList` (older list API) -> likely same `cmd 0x06` family with different struct version **[medium]**
- `IDOV3NoticeDialChange` -> likely async notice/callback in dial subsystem (not clearly a unique wire `cmd` in provided captures) **[low-medium]**
- `IDOV3SetDialSort` -> likely dial operation in `cmd 0x08` family (possibly another `operate`) **[medium]**

## Open questions

- Exact `cmd 0x08` request/response struct offsets (full field-by-field decode) still need formal mapping.
- Whether "set dial sort" is a distinct v3 cmd or just an `operate` variant on `0x08`.
- Whether "notice dial change" appears only as app-level event callback or also as dedicated wire command in other traces.

