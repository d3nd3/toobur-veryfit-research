---
id: 030
title: Coordinator capability flags — unlock stock Gadgetbridge UI
status: closed
labels: [enhancement, ui]
priority: P2
created: 2026-06-19
depends_on: []
blocks: []
---

## Problem

`TooburCoordinator` declares SpO₂/stress/sleep sample providers but omits several `supports*()` overrides that peer bands use to **turn on built-in Gadgetbridge screens** (charts, weather, workouts, live data). Defaults in `AbstractDeviceCoordinator` are `false`, so GB hides UI even when protocol work exists or is in progress.

## Flags to add (with peer reference)

| Method | Peer | Toobur protocol | Unlocks in GB |
|--------|------|-----------------|---------------|
| `supportsWeather()` | Moyoung, CMF, FitPro, ZeTime | SET `2D` + `0A 01` [013](../013-weather-push-0a-01/) | Global weather provider → watch push |
| `supportsRealtimeData()` | Moyoung, Lefun, FitPro | GET `02 A0` live steps/HR | Live activity / realtime charts |
| `supportsHeartRateMeasurement()` | Moyoung, CMF, Lefun | v3 type `03`, v3 `09` | HR measurement + chart entry points |
| `supportsRemSleep()` | Moyoung, CMF | v3 type `07` [006](../006-sleep-sync-v3-type-07/) | REM stage in sleep charts |
| `supportsRecordedActivities()` | CMF, Moyoung, Xiaomi | v3 type `04` [008](../008-workouts-v3-type-04/) | Workout / activity summary list |
| `getStressRanges()` | CMF (`1,30,60,80`), Xiaomi | stress samples exist | Colored stress zones in charts |
| `getHeartRateMeasurementIntervals()` | Moyoung, ZeTime, CMF | `toobur_hr_interval_seconds` list | Standard `HeartRateCapability` API |

Enable each flag only when the linked issue’s acceptance criteria are met, or gate behind a conservative subset (e.g. HR + sleep once [006](../006-sleep-sync-v3-type-07/) / [007](../007-hr-day-v3-type-03/) closed).

## GB touchpoints

- `gadgetbridge/.../devices/toobur/TooburCoordinator.java` — override methods above
- Optional: `supportsActiveCalories()` / `supportsActivityDistance()` if v3 type `08` day metrics are chart-ready

## Acceptance criteria

- [x] Each enabled flag has a linked closed or in-progress sync/parser issue
- [x] No crash when user opens a GB screen for a flag that is `true` but data empty
- [x] Stress chart uses sensible `getStressRanges()` (document chosen thresholds)
- [x] README “Already working” section updated when flags flip

## Comments

<!-- UI audit 2026-06-19 -->

### 2026-06-19 — closed

- `TooburCoordinator`: `supportsRealtimeData` true (GET `02 A0` wired); `supportsRemSleep` gated on ex func-table `v3Sleep` bit (optimistic when no ex table); `getStressRanges` CMF thresholds `{1,30,60,80}`; `getHeartRateMeasurementIntervals` aligned with `toobur_hr_interval_values` (5 s / 3 min remain on Toobur-specific pref only).
- Pre-existing: `supportsWeather` (base gate), `supportsRecordedActivities`, `supportsHeartRateMeasurement`.
- Test: `TooburCoordinatorTest`.
- README: `gadgetbridge/README_TOOBUR.md`, `issues/README.md` “Already working”.
- Next: issue 029 tabbed settings or 032 device card polish.
