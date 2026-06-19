---
id: 008
title: Workout sessions — v3 health type 04 → ActivitySummary
status: closed
labels: [enhancement]
priority: P1
created: 2026-06-19
depends_on: [002]
blocks: []
---

## Problem

Individual **workout records** (v3 type **`04`**) sync but are discarded. User wants workouts in GB activity/workout list.

## Wire

- v3 `04` **dataType `0x04`**, byte14=`00`
- Parser: `htmlapp/confirmed-only.html` `parseV3Activity` / workout record layout
- Prior art: `CmfWorkoutSummaryParserTest` pattern

## Captures

- `packetdumps/logcat/sync_example.txt`

## GB touchpoints

- New parser → `BaseActivitySummary` / `ActivitySummaryData`
- `TooburCoordinator.supportsActivityDataFetching` or workout-specific flags
- `TooburV3HealthSync.dispatchV3Reply` — wire type `04`

## Acceptance criteria

- [x] Fixture test parses at least one workout (sport type, duration, HR stats)
- [x] Workouts appear in GB after manual sync
- [x] Manifest entry `gb-wired`

## Comments

**2026-06-19 (issue 008 closed):**
- `TooburV3ActivityParser` + `TooburWorkoutSummaryParser` + `TooburWorkoutStore`; `dispatchV3Reply` type `0x04` → `BaseActivitySummary` persist.
- `TooburCoordinator`: `supportsRecordedActivities`, `getActivitySummaryParser`, `BaseActivitySummaryDao` in device DAO map.
- Fixture: synthetic `workout_v3_type04_sample.rx.hex` from `confirmed-only.html` simulateActivityRx (`sync_example.txt` has empty activity payload).
- Sport type 48 maps to `ActivityKind.UNKNOWN` until IDO enum table captured; core stats (duration, steps, HR) wired.
