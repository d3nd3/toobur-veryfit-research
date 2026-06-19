---
id: 021
title: Camera remote + sleep period (APP 06 02, SET 03 31)
status: closed
labels: [enhancement]
priority: P3
created: 2026-06-19
depends_on: [002, 024]
blocks: []
---

## Problem

Optional watch interactions with VALID bruteforce but no GB wiring. **Long-sit** moved to [015](../015-health-reminders/). **Device language** deferred — GET `02 31` unconfirmed on A200.

## Wire

| Command | Feature |
|---------|---------|
| APP `06 02` | Camera remote shutter |
| SET `03 31` | Sleep period / bedtime window |
| SET `03 13` | Shortcut (low priority) |

## Captures

- Camera: probe via [022](../022-bleak-live-probe-tooling/) if no logcat
- Sleep period: partial in sync dumps

## GB touchpoints

- Camera: GB camera intent + `06 02` TX fixture; optional **device card** shortcut like FitPro `DeviceCardAction.CameraAction` [032](../032-device-card-ui-polish/)
- Sleep period: pref under Health or Display tab [029](../029-tabbed-device-settings/); func-table gate via [024](../024-func-table-ui-gating/)

## Acceptance criteria

- [x] Camera shutter OR sleep period: TX fixture + settings toggle
- [x] Language/GET `31` listed under out-of-scope in issues README until captured

## Comments

**Closed 2026-06-19.** `TooburAppControlPackets` APP `06 02` start/stop + `TooburBleEventPackets` watch actions 556–561 → `GBDeviceEventCameraRemote` (pref-gated); `onCameraStatusChange` echoes APP `06 02` on phone open/close. `TooburSleepPeriodPackets` SET `03 31` probe + 7 B schedule; stock `devicesettings_sleep_time` on Health tab; `ex_main2.sleep_period` func-table gating. Device card camera shortcut deferred (032 slot limit). Next: issue 019 watch faces or 020 firmware OTA.
