# Watch faces — v3 dial commands

Gadgetbridge can **list** installed faces (v3 `0x06`) and **activate** an existing face (v3 `0x08`) when the extended func table reports `multi_dial`. Upload of custom `.iwf` files is **not shipped**.

## Shipped in Gadgetbridge

| Step | Wire | GB |
|------|------|-----|
| List | v3 GET `0x06` on `0x0AF6` → reply on `0x0AF2` | App Manager → refresh ( `onAppInfoReq` ) |
| Select | v3 SET `0x08` operate `1` + 31 B filename field | App Manager → Activate ( `onAppStart` ) |

Captures: [`packetdumps/live/2026-06-19_bind-v3.json`](../packetdumps/live/2026-06-19_bind-v3.json), [`ui_select_watch_face.txt`](../packetdumps/logcat/ui_select_watch_face.txt), [`ui_watch_face_write_json.txt`](../packetdumps/logcat/ui_watch_face_write_json.txt).

Tests: `TooburV3DialPacketsTest` (`v3-dial-list-06`, `v3-dial-set-08`).

## Upload blockers (v3 `0x07` + bulk `D1`)

VeryFit upload sequence from `ui_watch_face_write_json.txt`:

1. v3 `0x07` — device metadata (`Band 8`, screen size, …)
2. GET `0x02 0xF0` — MTU negotiate (137 B in capture)
3. Bulk `D1 01` — announce `.iwf.lz` path
4. Bulk `D1 05` / `D1 02` — chunked `.iwf` + embedded JSON dial definition
5. v3 `0x08` operate `1` — switch to new face after transfer

**Why not in GB yet:**

- Requires `.iwf` builder or shipping pre-built faces (VeryFit uses `mkIwfFile` JNI)
- Bulk `D1` compressor layout is large and device-specific
- Conn-param + MTU prelude must interleave with multi-minute transfer
- No live A200 upload probe in repo — only logcat from official app

**Next capture targets:** single small `.iwf` upload on A200; confirm `0x07` reply fields; validate `TooburV3BleChunkedWrite` on bulk channel.
