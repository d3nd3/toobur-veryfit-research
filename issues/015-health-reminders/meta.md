---
id: 015
title: Health reminders — long sit, drink, walk, menstrual (SET 20 / 60 / 47 / 41 / 42)
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [002, 024]
blocks: []
---

## Problem

VeryFit supports **long-sit**, **drink water**, **walk-around**, and **menstrual** reminders. None wired in GB device settings.

## Wire

| Key | Capture |
|-----|---------|
| `03 20` | Long-sit reminder (bruteforce VALID; capture via probe if missing) |
| `03 60` | `set_drinking_cont_*.txt` (16 B) |
| `03 47` | `set_walkaround_cont_*.txt` (17 B) |
| `03 41` | `set_woman_health_remind_*.txt` |
| `03 42` | send **after** `03 41` in dumps |

VeryFit often sends **v3 `09`** after SET `45`/`60` — mirror if needed for stress/drink toggles.

## GB touchpoints

- Prefer **reusing stock Gadgetbridge pref XML** (wire Toobur SET bytes in support class), not one-off Toobur keys where possible:
  - Long-sit → `devicesettings_inactivity_with_steps` or `devicesettings_inactivity_dnd` (CMF, Moyoung)
  - Drink water → `devicesettings_hydration_reminder_dnd` (CMF, C60, Lefun)
  - Walk-around → extend inactivity or dedicated screen under Health tab [029](../029-tabbed-device-settings/)
- Packet builders (template from captures like `TooburHealthSwitchPackets`)
- `TooburDeviceSpecificSettingsCustomizer` handlers — register every device-pushed key [031](../031-settings-customizer-wiring/)
- Func-table gating via [024](../024-func-table-ui-gating/) (CMF hides unsupported sub-prefs in shared health XML)

## Acceptance criteria

- [x] Each reminder type: TX fixture test + settings toggle
- [x] Schedule fields match capture defaults (interval, hours)
- [x] `gb-wired` for each enabled type in manifest

## Comments

**Closed 2026-06-19.** `TooburHealthReminderPackets` + `TooburHealthReminderPacketsTest` (drink/walk/menstrual captures; long-sit probe `03 20` + `protocol_long_sit` on enable). Health tab: stock `devicesettings_inactivity_with_steps`, `devicesettings_toobur_drink_water` (09:00–18:00, 30 min), walk + menstrual Toobur XML. `TooburSupport` connect + `onSendConfiguration`; func-table gates drink/walk/menstrual. Menstrual ON uses `AA` markers (no on capture — off from bind dump). Deferred: v3 `09` mirror after drink toggle; full long-sit ON capture. Next: issue 026 v3 HR full schedule or 023 SpO₂/stress schedules.
