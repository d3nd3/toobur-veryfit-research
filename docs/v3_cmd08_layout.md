# v3 `cmd 0x08` Layout Draft

This file proposes a practical byte-level layout for dial/watch-face v3 command `0x08` based on observed captures.

Related higher-level API doc:
- `research/repositories/Flutter_GitBook/zh/doc/IDOProtocolSimulatorExec/IDOV3Evt/IDOV3SetDial.md`

That doc says app JSON contains:
- `operate`
- `file_name` (max 29 bytes)
- `watch_file_size` (when feature enabled)

## Packet frame (observed)

All observed requests use:

- Header magic: `33 DA AD DA AD`
- Version: `01`
- Length: `2A 00`
- Cmd: `08 00`
- Sequence: little-endian at bytes `10..11`
- Fixed-size body after `nseq`
- CRC16 at final 2 bytes

Example request #1 (query-like):

`33 DA AD DA AD 01 2A 00 08 00 52 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 DF 1D`

Example request #2 (set-like with file name):

`33 DA AD DA AD 01 2A 00 08 00 53 01 01 77 69 74 63 68 32 2E 69 77 66 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 21 AD`

## Proposed body mapping (`byte 12` onward)

Best-fit with current evidence:

- `byte 12` -> `operate` (u8)
  - `00` in query-like packet
  - `01` in set-like packet
- `bytes 13..41` -> `file_name` C-string region (29 bytes)
  - in set example: `"witch2.iwf"` then zero padding
  - in query example: all zero
- `byte 42..43` -> CRC16-CCITT (LE)

This is consistent with "file_name max 29 bytes".

## RX pattern notes

Observed replies for matching `nseq`:

- `RX ... 08 00 52 01 00 00 77 69 74 63 68 32 2E 69 77 66 ...`
- `RX ... 08 00 53 01 00 01 77 69 74 63 68 32 2E 69 77 66 ...`

Interpretation (tentative):

- `byte 12` in RX likely `err_code` (`00` success)
- `byte 13` in RX likely `operate`
  - `00` for query reply
  - `01` for set reply
- `bytes 14..` include `file_name` string

This matches GitBook response fields: `err_code`, `operate`, `file_name`, `file_count`.
`file_count` may be present in trailing bytes in other captures/firmware variants; not fully mapped here.

## Offsets table (request)

- `0..4`  : `33 DA AD DA AD`
- `5`     : version `01`
- `6..7`  : length (`2A 00` in observed requests)
- `8..9`  : cmd (`08 00`)
- `10..11`: nseq LE
- `12`    : operate
- `13..41`: file_name[29] (ASCII + zero pad)
- `42..43`: CRC16 LE

## Confidence

- `operate @ byte12`: **high**
- `file_name @ 13..41 (29 bytes)`: **high**
- `watch_file_size` placement for `operate=3`: **unknown**
- complete RX field ordering (`err_code`, `operate`, `file_count`) for all variants: **medium**

## Next reverse-engineering steps

- Capture an explicit `operate=2` (delete) transaction and diff bytes.
- Capture an explicit `operate=3` (dynamic space / size) transaction to locate `watch_file_size`.
- Correlate with additional firmware where `v3WatchDailSetAddSize` is enabled.

