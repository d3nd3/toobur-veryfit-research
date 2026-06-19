---
id: 007
title: HR day history — v3 health type 03 → GB heart-rate chart
status: closed
labels: [enhancement]
priority: P1
created: 2026-06-19
depends_on: [002, 006, 026]
blocks: []
---

## Problem

`TooburV3HrParser` parses HR-day sync but **does not persist** to DB or stock HR chart.

## Wire

- v3 `04` **dataType `0x03`**, byte14=`01`
- Parser: `TooburV3HrParser`, `htmlapp/toobur-hr-csv.html`

## Captures

- `packetdumps/logcat/sync_example.txt`

## GB touchpoints

- Persist parsed HR points (time series sample provider or extend ID115 samples)
- `TooburCoordinator` — enable HR history / chart hooks GB expects
- `TooburV3FetchHealthOperation` persist listener for type `03`

## Acceptance criteria

- [x] Fixture test: HR-day hex → list of (timestamp, bpm) samples
- [x] GB Charts shows intraday HR after sync
- [x] Works with existing v3 `09` continuous HR toggle

## Comments

**2026-06-19 — closed**

- `TooburHrStore` + `TooburV3ProtocolCodec.parseV3HrHealthSyncReply` test seam.
- `TooburV3FetchHealthOperation.persistHr` → `ID115ActivitySample` (steps=0, HR bpm per minute).
- `TooburCoordinator`: `supportsHeartRateStats` + `supportsHeartRateMeasurement`.
- Manifest `hr-sync-v3-03` at `gb-wired`; synthetic JNI-7003 fixture (sync_example has empty HR payload).
- v3 `09` continuous HR toggle unchanged (issue 026 for full schedule payloads).
