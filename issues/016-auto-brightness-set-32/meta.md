---
id: 016
title: Auto night brightness — SET 03 32 + optional GET 02 B0
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [002, 024]
blocks: []
---

## Problem

Scheduled auto brightness (e.g. 19:00–06:00) not in GB. A200 uses SET **`03 32`** (12 B).

## Wire

| | Example |
|---|---------|
| Auto on 19:00–06:00 | `03 32 28 01 00 03 13 00 06 00 00 05` |
| Auto off | `03 32 28 01 00 01 …` |

## Captures

- `set_auto_brightness_on_19pm_to_6am.txt`, `set_auto_brightness_off.txt`

## GB touchpoints

- Prefer `devicesettings_screen_auto_brightness` + schedule times (stock GB) under Display tab [029](../029-tabbed-device-settings/), or extend `devicesettings_toobur.xml` if A200 payload does not match generic screen
- `TooburSupport.onSendConfiguration`
- Optional SET `03 31` sleep period if paired in VeryFit flow
- Func-table gate: `night_auto_brightness` bit via [024](../024-func-table-ui-gating/)

## Acceptance criteria

- [x] Fixture tests on/off payloads
- [x] User can enable scheduled auto brightness from device settings

## Comments

**2026-06-19 — closed**

- `TooburAutoBrightnessPackets` + `TooburAutoBrightnessPacketsTest` (`set-auto-brightness-03-32`, gb-wired).
- Display tab: stock `screen_auto_brightness` toggle + `toobur_auto_brightness_start`/`end` (19:00–06:00 defaults); `onSendConfiguration` + connect apply.
- Func-table gate: `night_auto_brightness` hides prefs when ex table present and bit clear.
- GET `02 B0` readback deferred (optional in spec).
