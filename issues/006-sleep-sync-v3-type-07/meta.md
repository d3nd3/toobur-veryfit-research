---
id: 006
title: Sleep sync — v3 health type 07 → GB sleep chart
status: closed
labels: [enhancement]
priority: P0
created: 2026-06-19
depends_on: [002]
blocks: []
---

## Problem

v3 type **`07`** is fetched but **not parsed or stored**. User wants sleep in Gadgetbridge stock sleep chart.

## Wire

- v3 `05` sizes → v3 `04` START/STOP with **dataType `0x07`**, byte14=`00`
- Parser spec: [`LATEST_SYNC_PARSING.md` §8](../../LATEST_SYNC_PARSING.md)
- Reference JS: `htmlapp/confirmed-only.html` `parseV3SleepSummary`

## Captures

- `packetdumps/logcat/sync_example.txt` (sleep stream in full sync)

## GB touchpoints

- New `TooburV3SleepParser` + persist hook in `TooburV3FetchHealthOperation`
- Sleep sample provider + `TooburCoordinator.supportsSleep()` (or equivalent GB API)
- Reuse `TooburV3HealthSync.V3ReassemblyBuffer`

## Acceptance criteria

- [x] RX fixture test → sleep summary domain object (stages, total minutes)
- [x] Manual fetch stores sleep; visible in GB sleep tab
- [x] `rx-confirmed` then `gb-wired` in manifest

## Comments

**2026-06-19 — closed**

- `TooburV3HealthSync`: dispatch v3 type `0x07` → `onV3SleepParsed`.
- `TooburSleepStore` + `TooburV3FetchHealthOperation.persistSleep` → `GenericSleepStageSample`.
- `TooburActivitySampleProvider` merges sleep stages into activity samples for stock sleep chart.
- `TooburCoordinator`: `supportsSleepMeasurement`, `GenericSleepStageSampleDao` in device DAO map.
- Manifest `sleep-sync-v3-07` at `gb-wired`; `TooburSleepStoreTest` + CI guard updated.
