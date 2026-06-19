---
id: 018
title: Connect-time sync — func table, user info, GET readbacks
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [010]
blocks: [024, 027]
---

## Problem

VeryFit on connect sends **GET `02 02`/`07`**, **SET `03 10`/`11`**, conn param **`03 35`**, etc. GB skips most — causes feature mismatch and prevents **func-table gating** of optional prefs.

## Wire (from `app_fresh_launch.txt`)

| Step | Command |
|------|---------|
| Func table | GET `02 02`, `02 07` |
| User profile | SET `03 10` (10 B), `03 11` (17 B) |
| Conn param | SET `03 35` 01 then 02 |
| v3 func | v3 `1A` |
| Misc | SET `03 E3 10 02` |

## GB touchpoints

- `TooburSupport.initializeDevice()` — ordered connect sequence closer to VeryFit
- Fetch + store raw func table bytes (parsing/UI gating → issue [024](../024-func-table-ui-gating/))
- `func-tables/function_table.json` as reference for bit meanings

## Acceptance criteria

- [x] GET `02 02`, `02 07`, v3 `1A` queued on connect; replies logged/stored
- [x] SET `03 10`/`03 11` sent when GB user profile available (full builders → issue [027](../027-units-user-profile-set-03-11/))
- [x] Conn param SET `03 35` two-step matches capture
- [x] No regression on connect time (<30s acceptable)

## Comments

**Closed 2026-06-19.** `TooburConnectSyncPackets` + `TooburFuncTablePackets`; `queueConnectSync()` runs after MTU in deferred init (GET 02 02/07, v3 1A, SET 03 10/11/35/E3). Func-table replies stored as hex in device prefs (`toobur_func_table_*_hex`). v3 1A GET is 14 B (no payload byte before CRC). Units tail uses A200 bind constants; imperial/timeformat polish deferred to issue 027. Next: issue 024 func-table UI gating.
