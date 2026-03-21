# v3 `cmd 0x06` Layout Draft

This file proposes a practical byte-level layout for dial list command `0x06` from observed captures.

Related higher-level API doc:
- `research/repositories/Flutter_GitBook/zh/doc/IDOProtocolSimulatorExec/IDOV3Evt/IDOV3GetDailLIstNew.md`

That doc describes "V3 get dial list (new)" returning:
- counts (`local_watch_num`, `cloud_watch_num`, etc.)
- current dial name
- list entries (`type`, `watch_version`, `sort_number`, `name`, `size`)

## Packet frame (observed)

Common v3 frame:

- Header magic: `33 DA AD DA AD`
- Version: `01`
- Length: little-endian `[6..7]`
- Cmd: little-endian `[8..9]` -> `06 00`
- Sequence: little-endian `[10..11]`
- Payload
- CRC16 at end

## Request shape (`cmd 0x06`)

Observed requests are short:

- Example:
  - `33 DA AD DA AD 01 0B 00 06 00 4E 01 4A F5`
- Interpreted:
  - `0..4` magic
  - `5` version
  - `6..7` length (`0B 00`)
  - `8..9` cmd (`06 00`)
  - `10..11` nseq (`4E 01`)
  - `12..13` CRC

So request payload appears empty/minimal on this firmware.

## Response shape (`cmd 0x06`)

Responses are variable-length and include list-like data:

- Example from `ui_select_watch_face.txt`:
  - `33 DA AD DA AD 01 36 00 06 00 4E 01 01 03 00 01 00 1C 01 01 07 00 00 00 6C 6F 63 61 6C 5F 31 01 07 00 00 00 6C 6F 63 61 6C 5F 32 01 07 00 00 00 6C 6F 63 61 6C 5F 33 ...`
- Example from `ui_watch_face_write_json.txt`:
  - `... 01 04 00 00 00 1C 01 01 07 00 00 00 6C 6F 63 61 6C 5F 31 ... 01 0A 00 00 00 77 69 74 63 68 32 2E 69 77 66 ...`

ASCII names are visible in payload:
- `local_1`
- `local_2`
- `local_3`
- `witch2.iwf`

This strongly matches "get dial list" semantics.

## Tentative payload interpretation

Current best guess for response body after `nseq`:

- first bytes: status/version/count metadata
- then repeated list items containing:
  - a small type/flag byte
  - a name-length (or fixed width marker)
  - ASCII name bytes (zero-terminated or length-delimited)

What is clear:
- names are embedded plainly in payload
- each response is tied to request `nseq`

What is not fully pinned yet:
- exact offsets of all counters (`local_watch_num`, etc.)
- exact item struct boundaries for every firmware variant
- whether size/version fields are always present

## Offsets table (stable header only)

- `0..4`  : `33 DA AD DA AD`
- `5`     : version `01`
- `6..7`  : length
- `8..9`  : cmd (`06 00`)
- `10..11`: nseq LE
- `12..N-3`: payload (variable)
- `N-2..N-1`: CRC16 LE

## Confidence

- `0x06` is dial-list query family: **high**
- short request with no meaningful body: **high**
- response contains dial names/list entries: **high**
- full field-level decode equivalent to GitBook JSON fields: **medium/low** (needs more captures + diffing)

## Next reverse-engineering steps

- Capture multiple list states with different known counts and diff first 12-20 payload bytes.
- Capture with/without cloud/wallpaper dials to identify count-field offsets.
- Build a small parser script that scans payload for ASCII name chunks and correlates preceding bytes as per-item headers.

