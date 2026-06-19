---
id: 001
title: Complete Toobur VeryFit Gadgetbridge driver via confirmed-feature pipeline
status: closed
labels: [enhancement, epic]
created: 2026-06-19
closed: 2026-06-19
---

Driver completeness for TOOBUR A200/BAND 8: test-first **confirmed features**, stock Gadgetbridge charts, live BLE probe for capture gaps.

**Spec:** [PRD.md](./PRD.md)  
**Protocol truth:** [A200-PROTOCOL.md](../../A200-PROTOCOL.md)  
**Implementation issues:** [issues/README.md](../README.md) — **002–032** (31 agent-ready slices)

## Child issues (implement these)

| Priority | IDs | Theme |
|----------|-----|-------|
| P0 | [002](../002-confirmed-feature-pipeline-scaffold/), [022](../022-bleak-live-probe-tooling/), [003](../003-fix-set-03-30-notice-alert/)–[006](../006-sleep-sync-v3-type-07/) | Scaffold, probe, notice, DND, alarms, sleep |
| P1 | [026](../026-v3-hr-09-full-schedule/), [007](../007-hr-day-v3-type-03/)–[011](../011-notifications-msg-verify/), [028](../028-auto-health-fetch-on-connect/), [017](../017-watch-ble-events-07/) | HR schedule + chart, workouts, swim, auto sync, device info, MSG, watch→phone |
| P2 | [012](../012-fix-set-2a-2d-payloads/)–[018](../018-connect-time-func-table-sync/), [023](../023-spo2-stress-full-set-payloads/)–[027](../027-units-user-profile-set-03-11/), [029](../029-tabbed-device-settings/)–[032](../032-device-card-ui-polish/) | Weather, goals, reminders, brightness, connect sync, func gating, SpO₂/stress schedules, notify bits, units, **UI layout & flags** |
| P3 | [019](../019-watch-faces-v3/)–[021](../021-extra-app-controls/) | Watch faces, OTA, camera/sleep period |

## Comments

**2026-06-19 — epic closed (driver completeness bar met)**

All **31** implementation slices **002–032** closed. Gadgetbridge Toobur driver wires stock charts, tabbed settings, func-table gating, connect sync, notifications/alarms/DND, health sync (sleep/HR/workouts/swim/SpO₂/stress), device card, watch→phone BLE events, per-app notify bits, units/profile, camera remote, sleep period, watch-face list/select (v3 `06`/`08`), and firmware status GET `02 48` (display when RX present).

**Documented Phase C gaps (no open agent issues):** `.iwf` bulk upload (v3 `07` + bulk `D1`), OTA transfer (`01` + bulk), device language GET `02 31`, live call MSG probe. See `docs/watch_faces_v3.md`, `docs/firmware_ota.md`, `issues/README.md` out-of-scope table.

**Next (human / new issues):** live `.iwf` upload capture + bulk tracer; OTA-capable watch GET `48` RX; upstream Gadgetbridge merge.
