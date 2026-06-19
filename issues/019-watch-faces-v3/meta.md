---
id: 019
title: Watch faces — v3 06 / 07 / 08 + bulk transfer
status: closed
labels: [enhancement]
priority: P3
created: 2026-06-19
depends_on: [002, 024]
blocks: []
---

## Problem

User wants to **change watch face** from Gadgetbridge. Requires v3 dial commands + `.iwf` bulk on `0x0AF1`.

## Wire

| v3 cmd | Role |
|--------|------|
| `06` | **Get** dial list (installed faces) |
| `07` | Write dial metadata (before bulk) |
| `08` | **Set** active dial |
| Bulk `D1` | `.iwf` / compressed face file on `0x0AF1` |

## Captures

- `ui_select_watch_face.txt`, `ui_watch_face_write_json.txt`
- [`docs/v3_dial_cmds.md`](../../docs/v3_dial_cmds.md)

## GB touchpoints

- New coordinator capability + settings UI or reuse GB watchface install flow if compatible
- Chunked write reuse from `TooburV3BleChunkedWrite`
- Large scope — split list/select vs upload if needed

## Acceptance criteria

- [x] List faces from watch (v3 `06`)
- [x] Select existing face on watch
- [x] Upload custom `.iwf` (stretch — document blockers)

## Comments

**2026-06-19 — closed (list + select shipped; upload documented)**

- `TooburV3DialPackets` + `TooburV3DialPacketsTest`: GET `0x06` list parser, SET `0x08` 31 B payload; fixtures from bind-v3 + logcat.
- `TooburSupport`: `onAppInfoReq` / `onAppStart` on `0x0AF6`; `0x0AF2` reassembly when `multi_dial` func bit set.
- `TooburCoordinator`: `supportsWatchfaceManagement` / `supportsAppsManagement` gated by `isMultiDial()`.
- `docs/watch_faces_v3.md`: upload blockers (`0x07`, bulk `D1`, mkIwfFile, MTU prelude).
- Upload not sent — next iteration needs live `.iwf` bulk capture + transfer coordinator.
