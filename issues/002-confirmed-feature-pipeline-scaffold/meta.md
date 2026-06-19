---
id: 002
title: Confirmed-feature pipeline scaffold (codec tests + manifest)
status: closed
labels: [enhancement, infrastructure]
priority: P0
created: 2026-06-19
depends_on: []
blocks: [003, 004, 005, 006, 007, 008, 009, 010, 011]
---

Foundation for all other Toobur issues. No GB UI wiring until parsers pass fixture tests.

## Problem

Agents need a repeatable path: capture hex → JUnit fixture test → manifest entry → GB wiring. Nothing exists yet.

## Protocol reference

- [`A200-PROTOCOL.md`](../../A200-PROTOCOL.md) — evidence hierarchy, confirmation stages
- [`issues/001/PRD.md`](../001-complete-toobur-gadgetbridge-driver/PRD.md) — feature confirmation pipeline

## Implementation

1. **`docs/confirmed-features.md`** — table: feature id | wire | stage | test class | capture source
2. **`@ConfirmedFeature`** annotation + **`ConfirmedFeaturesTest`** CI guard (manifest ↔ tests)
3. **`gadgetbridge/app/src/test/resources/toobur/fixtures/`** directory
4. **`scripts/extract_logcat_fixtures.py`** — pull TX/RX hex from `packetdumps/logcat/`
5. Link to [issue 022](../022-bleak-live-probe-tooling/) for Bleak live capture when logcat missing
6. **Protocol codec package** (or extend `TooburV3HealthSync`) as single test seam
7. **First tracer:** sleep v3 type `07` RX parser test from `sync_example.txt` (parser only, no GB chart yet — that's issue 006)

## Acceptance criteria

- [x] `./gradlew :app:test` runs at least one Toobur fixture test
- [x] `docs/confirmed-features.md` lists sleep-sync with stage `rx-confirmed` when parser test passes
- [x] `ConfirmedFeaturesTest` fails if annotation and manifest drift

## Comments

**2026-06-19 — closed**

- Added `docs/confirmed-features.md`, `@ConfirmedFeature`, `ConfirmedFeaturesTest`, `scripts/extract_logcat_fixtures.py`.
- Codec seam: `TooburV3ProtocolCodec` + `TooburV3SleepParser`; fixtures under `app/src/test/resources/toobur/fixtures/`.
- First `rx-confirmed` feature: `sleep-sync-v3-07` (`TooburV3SleepParserTest`); GB chart wiring deferred to issue 006.
- Tests run via `./gradlew :app:testBanglejsDebugUnitTest --tests '…toobur.*'` (banglejs flavor).
- Unblocked compile: `addGBActivitySamples` now takes `List` in Toobur fetch/activity sync.
- **Live probe (optional stage 3):** when logcat lacks a feature, run `scripts/toobur_ble_probe.py` → `packetdumps/live/*.txt`, then `scripts/extract_logcat_fixtures.py` into JUnit fixtures. See README “When to probe vs logcat”.
- Next: issue 011 MSG verify (probe unblocked), issue 003 notice alert.
