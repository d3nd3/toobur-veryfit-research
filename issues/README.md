# Issues (local tracker)

PRDs and work items for the Toobur A200 Gadgetbridge driver.  
**Protocol truth:** [`A200-PROTOCOL.md`](../A200-PROTOCOL.md)

## Layout

```
issues/
├── README.md                 ← index (this file)
├── 001-…/                    ← epic PRD
└── <NNN>-<slug>/
    └── meta.md               ← agent-ready issue spec
```

## Agent workflow

1. Pick an issue with `status: ready-for-agent`
2. Read `meta.md` → wire section in `A200-PROTOCOL.md` → captures in `packetdumps/logcat/`
3. Follow confirmation pipeline ([issue 002](./002-confirmed-feature-pipeline-scaffold/)): fixture test → GB wiring → update manifest
4. Set `status: closed` when acceptance criteria met

## Index

### Epic

| ID | Title | Status |
|----|-------|--------|
| [001](./001-complete-toobur-gadgetbridge-driver/) | Complete Toobur VeryFit Gadgetbridge driver (PRD) | `ready-for-agent` |

### P0 — infrastructure & wrong wire

| ID | Title | Depends | Status |
|----|-------|---------|--------|
| [002](./002-confirmed-feature-pipeline-scaffold/) | Confirmed-feature pipeline scaffold | — | closed |
| [022](./022-bleak-live-probe-tooling/) | Bleak live BLE probe for capture gaps | — | closed |
| [003](./003-fix-set-03-30-notice-alert/) | Fix SET `03 30` notice alert (20 B) | 002 | `ready-for-agent` |
| [004](./004-fix-set-03-29-dnd-schedule/) | DND schedule SET `29` + GET `30` | 002 | closed |
| [005](./005-v3-alarms-0e-0f/) | v3 alarms GET `0F` / SET `0E` (10 slots) | 002 | closed |
| [006](./006-sleep-sync-v3-type-07/) | Sleep sync → GB sleep chart | 002 | closed |

### P1 — charts, sync, device info, watch→phone

| ID | Title | Depends | Status |
|----|-------|---------|--------|
| [026](./026-v3-hr-09-full-schedule/) | v3 HR cmd `09` full schedule payloads | 002 | closed |
| [007](./007-hr-day-v3-type-03/) | HR day history → GB HR chart | 002, 006, 026 | closed |
| [008](./008-workouts-v3-type-04/) | Workout sessions → ActivitySummary | 002 | closed |
| [009](./009-swim-v3-type-06/) | Swim sessions v3 type `06` | 002, 008 | closed |
| [028](./028-auto-health-fetch-on-connect/) | Automatic v3 health fetch on connect | 006, 018 | closed |
| [010](./010-device-info-card/) | Full device info card | — | `closed` |
| [011](./011-notifications-msg-verify/) | Verify MSG `05` notifications | 002, 003, 022 | closed |
| [017](./017-watch-ble-events-07/) | Watch BLE events `07 40` + call/music | — | closed |

### P2 — settings & capability gating

| ID | Title | Depends | Status |
|----|-------|---------|--------|
| [012](./012-fix-set-2a-2d-payloads/) | Fix SET `2A` / `2D` payload lengths | 002 | closed |
| [013](./013-weather-push-0a-01/) | Weather push `0A 01` data | 012, 024 | closed |
| [014](./014-goals-set-03-43/) | Goals SET `03`/`04`/`43` | 002 | closed |
| [015](./015-health-reminders/) | Long sit, drink, walk, menstrual reminders | 002, 024 | closed |
| [016](./016-auto-brightness-set-32/) | Auto brightness SET `32` | 002, 024 | closed |
| [018](./018-connect-time-func-table-sync/) | Connect-time GET/SET sequence | 010 | closed |
| [024](./024-func-table-ui-gating/) | Parse func table + gate GB UI | 018 | closed |
| [023](./023-spo2-stress-full-set-payloads/) | SpO₂/stress full SET `44`/`45` schedules | 002, 024 | closed |
| [025](./025-per-app-notification-switches/) | Per-app notify GET `02 10` + item bytes | 003, 024 | `ready-for-agent` |
| [027](./027-units-user-profile-set-03-11/) | Units SET `03 11` + user profile | 018, 024 | `ready-for-agent` |
| [029](./029-tabbed-device-settings/) | Tabbed device settings (DeviceSpecificSettingsScreen) | — | closed |
| [030](./030-coordinator-ui-capability-flags/) | Coordinator flags — unlock stock GB UI | — | closed |
| [031](./031-settings-customizer-wiring/) | Settings customizer — wire prefs on change | — | closed |
| [032](./032-device-card-ui-polish/) | Device card icons + quick toggles | 010 | closed |

### P3 — advanced

| ID | Title | Depends | Status |
|----|-------|---------|--------|
| [019](./019-watch-faces-v3/) | Watch faces v3 + bulk | 002, 024 | `ready-for-agent` |
| [020](./020-firmware-ota/) | Firmware OTA + GET `48` | 010 | `ready-for-agent` |
| [021](./021-extra-app-controls/) | Camera remote + sleep period | 002, 024 | `ready-for-agent` |

## Suggested agent order

```
002 + 022 (parallel — scaffold + probe tooling)
002 → 003, 004, 005, 006 (parallel after 002)
006 → 007, 028
002 → 026 → 007
002 → 008 → 009
010 → 018 → 024
024 → 013, 015, 016, 019, 021, 023, 025, 027
029–032 (UI polish — parallel with P2 protocol work; 031 before 013 weather QA)
003 → 011 (022 helps fixture gaps)
017 (opportunistic — watch→phone; pair with 004 for DND readback)
010 → 020
```

## Already working in GB (no issue needed)

Bind, battery, time, restart, raise-to-wake, wrist, orientation, **activity goals (steps/sleep/calorie+distance)**, v3 health fetch skeleton, SpO₂/stress **day sync + charts**, auto sport `49`, find phone/device, music APP control, sport summary chart (v3 type `08`), live data GET `A0`, **device card info** (GET `02 01`/`04`/`A7`, last sync), **device card quick actions** (HR/SpO₂/stress/**DND** with themed icons), **coordinator stock-chart flags** (realtime, REM sleep, workouts, stress zones, HR intervals, weather), **tabbed device settings** (Generic/Display/Health/Notifications/Connection/Developer), **scheduled auto brightness** (SET `03 32` on Display tab, func-table gated), **health reminders** (long-sit `03 20`, drink `03 60`, walk `03 47`, menstrual `03 42`/`41` on Health tab), **v3 HR continuous schedule** (cmd `09` reset+mode+schedule; interval pref; no legacy SET `03 25`), **SpO₂/stress continuous SET schedules** (`03 44`/`03 45` full payloads + Health tab window prefs).

Notice alert is **not** fully polished — see 003.

## Explicitly out of scope (no issue until captured)

| Topic | Reason |
|-------|--------|
| Blood sugar, weight, VO2Max sync | Not in A200 v3 health types |
| SET `03 52` real-time sensor | Wire purpose unconfirmed |
| BIND encrypted auth `04 05` | No capture; bind manual path works |
| GPS GET `A3`–`A5` | A200 has no GPS (`gps_platform=0`) |
| Device language GET `02 31` | Bruteforce not validated; defer to probe |
| Full VeryFit app parity | PRD completion bar = stock GB charts |

## External research

Hive vault (outside repo): `/home/dinda/storage/hive/SmartHome/Toobur Veryfit a200`  
Merged index: [`docs/external-notes/HIVE-A200-NOTES.md`](../docs/external-notes/HIVE-A200-NOTES.md)

## Triage

Edit `status:` in `meta.md`. Values: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`, `closed`.
