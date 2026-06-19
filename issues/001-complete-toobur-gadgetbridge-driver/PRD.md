# PRD: Complete Toobur VeryFit Gadgetbridge driver via confirmed-feature pipeline

## Problem Statement

The Gadgetbridge Toobur/VeryFit driver (Realtek 0x0AF0 / IDO protocol) is partially implemented: v3 health sync runs, and some metrics (SpO₂, stress, daily sport summary) persist, but many day-to-day capabilities still use legacy ID115 code paths or are fetch-only without Gadgetbridge integration. Notifications, calls, v3 alarms, sleep charts, HR-day history, workout sessions, and numerous device settings either use wrong wire formats, lack parsers, or never reach the database and stock Gadgetbridge UI.

The user runs the **banglejs** Gadgetbridge flavor for a multi-watch household (two Bangle.js devices plus one Toobur A200/BAND 8). They want **driver completeness** in the Gadgetbridge sense—every feature Gadgetbridge already exposes should work end-to-end with **stock chart integration**—not full VeryFit app parity. They also want a rigorous **confirmed-feature** process: capabilities are proven by tests against capture-derived fixtures (and live BLE probes when fixtures are missing) before any persistence or UI wiring.

## Solution

Introduce a **feature confirmation pipeline** for the Toobur driver:

1. **TX-confirmed** — packet builders match logcat/live-capture hex
2. **RX-confirmed** — parsers produce typed **response data** from fixture hex (JUnit, CI-safe)
3. **GB-wired** — persistence, coordinator flags, and stock Gadgetbridge charts/settings only after RX-confirmed

Build vertically per capability (not horizontal layers). Use existing logcat dumps and a **live BLE probe** (Python + Bleak on host USB adapter) to fill capture gaps during short on-demand sessions (watch disconnected from phone). Track progress in `docs/confirmed-features.md` synchronized with `@ConfirmedFeature` test annotations and a CI guard.

Target **canonical firmware**: TOOBUR A200/BAND 8 v3. Other IDO skins gated by func-table bits; no long-term dual implementations.

## User Stories

### Core pipeline & quality

1. As a developer, I want a confirmed-features manifest listing every capability with its confirmation stage (`tx-confirmed`, `rx-confirmed`, `gb-wired`), so that implementation progress is auditable and UI work cannot run ahead of parser proof.
2. As a developer, I want `@ConfirmedFeature` annotations on tests kept in sync with the manifest, so that CI can detect drift between docs and code.
3. As a developer, I want offline fixture tests under Gadgetbridge’s test suite, so that parsers and builders regress safely without a watch connected.
4. As a developer, I want a live BLE probe script on the host adapter, so that missing RX captures can be recorded into fixture files during short dev sessions.
5. As a developer, I want a logcat-to-fixture extractor, so that existing `packetdumps/` captures seed tests without manual hex copying.
6. As a maintainer, I want confirmation stages enforced by policy (no GB wiring before `rx-confirmed`), so that half-implemented features do not reach users.

### Connection, bind, device info

7. As a Toobur user, I want to manually send bind and unbind from device settings, so that I control VeryFit-style pairing without automatic bind on every connect.
8. As a Toobur user, I want device info (Bluetooth name, MAC, firmware, resource pack version, last sync time) shown on the device card, so that I can verify firmware and pairing state.
9. As a Toobur user, I want battery percentage and voltage displayed and updated, so that I know charge state accurately.
10. As a Toobur user, I want to restart the watch from Gadgetbridge, so that I can recover from glitches without physical buttons.

### Time, language, wrist

11. As a Toobur user, I want time synced to the watch on connect and on demand, so that alarms and health timestamps are correct.
12. As a Toobur user, I want to set wrist side (left/right), so that raise-to-wake and orientation match how I wear the band.
13. As a Toobur user, I want to set device language from Gadgetbridge where the firmware supports it, so that watch UI matches my locale.

### Notifications, calls, message center

14. As a Toobur user, I want phone notifications forwarded to the watch using the correct VeryFit MSG format, so that alerts appear reliably on A200 firmware.
15. As a Toobur user, I want incoming call alerts on the watch, so that I see who is calling without checking the phone.
16. As a Toobur user, I want call state updates (end/dismiss) sent to the watch, so that the call UI clears properly.
17. As a Toobur user, I want to answer or control calls from the watch where supported, so that I can use hands-free workflows.
18. As a Toobur user, I want SMS/message-style notifications handled with correct chunked encoding, so that longer text is not truncated or garbled.

### Alarms

19. As a Toobur user, I want to set and get alarms via Gadgetbridge’s alarm UI, so that wake alarms sync to the band.
20. As a Toobur user, I want v3 alarm commands (10 slots on A200) used instead of legacy 5-slot SET, so that all alarm slots match the official firmware.
21. As a Toobur user, I want alarm enable/disable, time, repeat, and snooze reflected accurately after sync, so that what I configure in GB matches the watch.

### Health sync — fetch & offsets

22. As a Toobur user, I want v3 health sync (`0x05` sizes then `0x04` per type) to run on manual fetch and auto-fetch, so that stored watch data reaches the phone.
23. As a Toobur user, I want incremental sync using stored offsets and total-byte comparison, so that unchanged data is not re-downloaded unnecessarily.
24. As a Toobur user, I want per-type sync scope prefs (off / manual / both), so that I control which health streams participate in fetch.
25. As a Toobur user, I want optional sport-stream offset probing for firmware quirks, so that advanced users can recover partial sport history if needed.

### Health sync — metrics & charts (stock Gadgetbridge UI)

26. As a Toobur user, I want SpO₂ history in Gadgetbridge’s SpO₂ chart, so that I can review blood oxygen trends (already partially wired; must stay confirmed by tests).
27. As a Toobur user, I want stress/pressure history in Gadgetbridge’s stress chart, so that I can review daily pressure readings.
28. As a Toobur user, I want sleep data parsed from v3 type `0x07` and shown in Gadgetbridge’s sleep chart, so that I see stages and duration after sync.
29. As a Toobur user, I want HR-day data from v3 type `0x03` in Gadgetbridge’s heart-rate chart, so that I see intraday HR series not just live HR.
30. As a Toobur user, I want daily steps, calories, distance, and active time from sport summary (`0x08`) in the activity chart, so that daily totals are reliable day-over-day.
31. As a Toobur user, I want intraday activity/workout records from v3 type `0x04` persisted as activity summaries, so that individual workouts appear in Gadgetbridge’s workout list.
32. As a Toobur user, I want swim sessions from v3 type `0x06` persisted where data exists, so that swim workouts appear alongside other activities.
33. As a Toobur user, I want live steps/HR via GET live data when enabled, so that I can see current values without a full sync.

### Health measurement toggles & reminders

34. As a Toobur user, I want continuous HR with configurable interval (including smart/dynamic mode), so that HR monitoring matches my preference.
35. As a Toobur user, I want to toggle continuous SpO₂ measurement on the band, so that I can balance accuracy and battery.
36. As a Toobur user, I want to toggle continuous stress/pressure measurement, so that I control stress tracking.
37. As a Toobur user, I want drinking-water reminder toggles, so that hydration nudges match my schedule.
38. As a Toobur user, I want walk-around reminder toggles, so that sedentary alerts match my preference.
39. As a Toobur user, I want menstrual cycle reminder toggles where supported, so that cycle tracking reminders work from Gadgetbridge settings.

### Goals & extended health (Phase B/C where confirmed)

40. As a Toobur user, I want step/sport/calorie/walking goals synced where the protocol exposes SET commands, so that watch goals match Gadgetbridge configuration.
41. As a Toobur user, I want distance and combined kcal+exercise+walking goal fields synced when confirmed by captures, so that goal screens on the watch stay accurate.
42. As a Toobur user, I want blood sugar, weight, VO2Max, and other extended metrics synced only after RX-confirmed parsers exist, so that unsupported metrics are not faked.

### Device settings & toggles

43. As a Toobur user, I want raise-to-wake toggled with the A200 9-byte SET payload, so that gesture wake matches captures.
44. As a Toobur user, I want Do Not Disturb with schedule (not just on/off), so that quiet hours match the official app behavior.
45. As a Toobur user, I want automatic night screen brightness with schedule, so that brightness drops during configured hours.
46. As a Toobur user, I want music control on the watch enabled/disabled, so that I control whether the band shows media controls.
47. As a Toobur user, I want weather push toggled and weather payloads sent when enabled, so that the watch face can show weather.
48. As a Toobur user, I want intelligent exercise recognition toggled, so that auto sport detection matches my preference.
49. As a Toobur user, I want Find My Phone enabled so the watch can signal the phone, so that I can locate my phone from the band.
50. As a Toobur user, I want find-device from the phone, so that I can locate the band when misplaced.
51. As a Toobur user, I want call/notification alert switches using the A200 20-byte SET `0x30` form, so that alert behavior matches firmware.

### Watch face & firmware (Phase C)

52. As a Toobur user, I want to change watch faces via Gadgetbridge when confirmed, so that I am not locked to the stock face.
53. As a Toobur user, I want firmware update checks when the OTA path is confirmed, so that I can update safely without the official app.

### Developer / research

54. As a developer, I want HTML protocol tools to remain the manual experiment surface, so that ad-hoc probing does not require rebuilding the APK.
55. As a developer, I want custom Toobur screens only for metrics Gadgetbridge has no stock chart for (e.g. raw v3 inspect, detailed sport diagnostics), so that maintenance stays focused on the codec and GB hooks.

## Implementation Decisions

### Architectural scope

- **Completion bar**: Gadgetbridge integration with stock charts—not VeryFit app parity (message center marketplace, OTA store UI, etc. are Phase C or out of scope until confirmed).
- **Canonical device**: TOOBUR A200 / BAND 8 v3 firmware; func-table gating for optional features on other IDO skins.
- **Build flavor**: Continue using **banglejs** Gadgetbridge flavor; Toobur driver changes live in the shared fork under the standard device support/coordinator pattern extending ID115.
- **Phasing**: Phase A (notifications, sleep, v3 alarms, HR-day, daily activity, scheduled DND/brightness) → Phase B (remaining logcat-confirmed toggles/reminders/goals) → Phase C (watch face upload, firmware OTA, blood sugar, VO2Max, menstrual data sync, message center parity).

### Primary test seam (one boundary)

All automated confirmation tests target a **single protocol codec boundary**:

- **Inbound**: reassembled wire payloads (classic 0x0AF7 frames or v3 `DA AD DA AD…` buffers after chunk reassembly)
- **Outbound**: typed **response data** and command parameter objects (sleep summary, alarm slot list, battery info, workout record, notification ACK expectations, etc.)
- **Outbound TX**: builder functions that produce exact TX byte sequences for a given command + parameters

The BLE service layer, database persistence, and Android UI **call** this codec but are **not** the primary test seam. Live BLE probe is **outside** CI: it only produces fixture files consumed by codec tests.

### Feature confirmation pipeline

Each capability progresses: `tx-confirmed` → `rx-confirmed` → `gb-wired`.

- Registry: `docs/confirmed-features.md` + `@ConfirmedFeature(id, stage)` on JUnit tests + `ConfirmedFeaturesTest` CI guard.
- Fixtures: `app/src/test/resources/toobur/fixtures/` from logcat extraction and live probe output.
- **No GB persistence or coordinator flags** until `rx-confirmed` for that feature ID.

### Bootstrap order (first vertical slices)

1. Scaffold manifest, annotation, fixture directory, logcat extractor
2. First `rx-confirmed`: **sleep** parser (v3 type `0x07`) from existing sync captures
3. Live probe smoke: GET battery (`0x02` `0x05`) via Bleak
4. First `gb-wired`: sleep → sleep sample provider + `supportsSleep()` + stock sleep chart
5. Then: notifications → v3 alarms → HR-day → sport summary → workouts → swim → schedules → toggles

### Gadgetbridge integration pattern (after rx-confirmed)

- **Stock chart integration** via sample providers + coordinator flags
- **Notifications/calls**: VeryFit MSG `0x05` + A200 SET `0x30`
- **Alarms**: v3 `0x0E`/`0x0F`, 10 slots on A200
- **Health fetch**: extend v3 fetch state machine per type
- **Settings**: schedule payloads for DND `0x29`, brightness `0x32`

### Live BLE probe

- Python + Bleak on host USB adapter; on-demand sessions (watch disconnected from phone)

### Func-table gating

- GET `0x02` `0x02` / `0x07` before optional prefs

## Testing Decisions

- Assert at **codec seam**: fixture hex → **response data**; parameters → TX hex
- **Vertical slices** per feature; CI = fixture JUnit only
- Prior art: `CmfWorkoutSummaryParserTest`, HTML parsers, existing Toobur v3 classes

## Out of Scope

- Full VeryFit parity (message center marketplace, cloud sync)
- Custom Toobur dashboard unless GB lacks a chart
- CI hardware tests
- Permanent legacy angelfit dual-stack
- Upstream Codeberg merge in this issue

## Further Notes

- See `CONTEXT.md` for ubiquitous language
- Grilling decisions: GB integration bar, A200 canonical, stock charts, test-first pipeline, live probe on demand
