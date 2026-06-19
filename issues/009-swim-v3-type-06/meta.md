---
id: 009
title: Swim sessions — v3 health type 06
status: closed
labels: [enhancement]
priority: P1
created: 2026-06-19
depends_on: [002, 008]
blocks: []
---

## Problem

Swim data (v3 type **`06`**) is synced but not parsed/stored.

## Wire

- v3 `04` **dataType `0x06`**, byte14=`00`
- Same fetch pipeline as other count-data types

## Captures

- `packetdumps/logcat/sync_example.txt` (if swim packets present; else live probe session)

## GB touchpoints

- Parser + persist (reuse workout/activity summary path from issue 008 where possible)
- Enable in v3 sync prefs (`toobur_v3_sync_swim_mode`)

## Acceptance criteria

- [x] Parser test or `needs-capture` documented in manifest
- [x] Swim sessions visible in GB activity when watch has swim data

## Comments

**2026-06-19 (issue 009 closed):**
- `TooburV3SwimParser` (v1 head_size=34: struct version @13, datetime @14) + `TooburSwimStore` + `TooburSwimSummaryParser`; `TooburActivitySummaryParser` routes swim vs workout raw blobs.
- `TooburV3HealthSync.dispatchV3Reply` type `0x06` → `BaseActivitySummary` persist; `toobur_v3_sync_swim_mode` already in fetch pipeline.
- Fixtures: `swim_v3_type06_sync_example.rx.hex` (empty date, parser null) + synthetic `swim_v3_type06_sample.rx.hex`.
- Lap/item payload (data_size>0) deferred — needs live capture via issue 022.
- Next iteration: issue 010 device info or issue 022 live probe.
