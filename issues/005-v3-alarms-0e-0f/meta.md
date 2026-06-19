---
id: 005
title: v3 alarms — GET 0F / SET 0E (10 slots)
status: closed
labels: [enhancement]
priority: P0
created: 2026-06-19
depends_on: [002]
blocks: []
---

## Problem

GB uses legacy SET `03 02` with **5 slots**. A200 uses v3 **`0F` get** / **`0E` set** with **10 alarm slots** (355-byte SET packet).

## Wire

| Cmd | Role |
|-----|------|
| v3 `0F` | GET alarms — `get_alarm.txt` |
| v3 `0E` | SET alarms + sport order — `set_alarms_and_sports.txt`, evt 5017 |

Chunked on **`0x0AF6`** / notify **`0x0AF2`** (same v3 route as HR `0x09`). Per-alarm: id, on/off (`AA`/`55`), hour, minute, repeat, etc.

## Captures

- `packetdumps/logcat/get_alarm.txt`
- `packetdumps/logcat/set_alarms_and_sports.txt`

## GB touchpoints

- Replace `TooburSupport.onSetAlarms()` legacy path
- `TooburCoordinator.getAlarmSlotCount()` → **10**
- `TooburV3BleChunkedWrite` for TX
- Port alarm block layout from `confirmed-only.html` or `LATEST_SYNC_PARSING.md`

## Acceptance criteria

- [x] GB alarm UI syncs 10 slots to watch via v3 `0E`
- [ ] Optional: GET `0F` on connect to reconcile watch → GB
- [x] Fixture tests for encode/decode one alarm slot
- [x] Remove or gate legacy SET `03 02` on A200

## Comments

**2026-06-19 — closed**

- `TooburV3AlarmPackets` + `TooburV3AlarmPacketsTest`: 34 B block encode/decode, GET `0x0F` TX, SET `0x0E` 353 B payload vs `set_alarms_and_sports.txt`.
- `TooburSupport.onSetAlarms`: v3 `0x0E` chunked on `0x0AF6`; legacy SET `03 02` removed.
- `TooburCoordinator.getAlarmSlotCount()` → 10.
- GET `0x0F` on connect + GB alarm DB reconcile deferred (parser ready via `parseGetPayload`).
- Next: issue 006 sleep chart wiring or issue 022 live probe.
