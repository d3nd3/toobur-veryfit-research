---
id: 004
title: DND schedule — SET 03 29 (14 B) + GET 02 30 readback
status: closed
labels: [enhancement]
priority: P0
created: 2026-06-19
depends_on: [002]
blocks: []
---

## Problem

GB sends 6-byte DND on/off. A200 uses **14-byte scheduled DND** and **GET `02 30`** for readback after SET.

## Wire

| | Bytes |
|---|--------|
| **SET on** | `03 29 AA 17 00 07 00 02 FE 55 17 00 07 00 00 00` |
| **SET off** | first payload byte `55` |
| **GET** | `02 30` → RX byte2 `AA`/`55` + schedule fields |
| **VBUS** | 116 SET_DND, 316 GET_DND |

## Captures

- `packetdumps/logcat/set_dnd_on.txt`, `set_dnd_off.txt`

## GB touchpoints

- `TooburSupport.applyDndFromPrefs()` — replace boolean with schedule model
- `devicesettings_toobur.xml` — add start/end time prefs (match VeryFit 23:00–07:00 default from captures)
- On SET success: queue GET `02 30` to verify
- After SET: watch may send `07 40` notifyType 16 — ACK + GET readback per [017](../017-watch-ble-events-07/)

## Acceptance criteria

- [x] Fixture tests for SET on/off + GET reply parse
- [x] Device settings UI exposes schedule (or sensible defaults with toggle)
- [x] `gb-wired` in confirmed-features manifest

## Comments

**2026-06-19 — closed**

- `TooburDndPackets` + `TooburDndPacketsTest`: 16 B SET (14 B payload) and GET `02 30` parse vs `set_dnd_*.txt`.
- `TooburSupport.applyDndFromPrefs`: schedule from `toobur_dnd_start`/`toobur_dnd_end` (default 23:00–07:00); queues GET readback after SET.
- `devicesettings_toobur.xml`: XTimePreference start/end under DND toggle.
- `07 40` notifyType 16 ACK path deferred to issue 017.
- Next: issue 005 v3 alarms or issue 022 live probe.
