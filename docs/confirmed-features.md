# Confirmed Toobur features

Registry for the [feature confirmation pipeline](../CONTEXT.md#feature-confirmation-pipeline). Each row must match a `@ConfirmedFeature` annotation on a JUnit test; `ConfirmedFeaturesTest` fails on drift.

**Stages:** `tx-confirmed` (TX builder matches capture) → `rx-confirmed` (parser fixture test passes) → `gb-wired` (Gadgetbridge persist + chart).

**Fixtures:** `gadgetbridge/app/src/test/resources/toobur/fixtures/`  
**Extract from logcat:** `scripts/extract_logcat_fixtures.py`  
**Live capture gaps:** [issue 022](../issues/022-bleak-live-probe-tooling/meta.md) (Bleak probe → same fixture format)

| Feature id | Wire | Stage | Test class | Capture source |
|------------|------|-------|------------|----------------|
| `set-notice-03-30` | SET `0x03 0x30` call/notice alert (20 B) | `gb-wired` | `TooburNoticeAlertPacketsTest` | `packetdumps/logcat/app_fresh_launch.txt` |
| `set-dnd-03-29` | SET `0x03 0x29` + GET `0x02 0x30` scheduled DND (14 B) | `gb-wired` | `TooburDndPacketsTest` | `packetdumps/logcat/set_dnd_on.txt`, `set_dnd_off.txt` |
| `sleep-sync-v3-07` | v3 cmd `0x04` dataType `0x07` | `rx-confirmed` | `TooburV3SleepParserTest` | `packetdumps/logcat/sync_example.txt` + synthetic sample fixture |
