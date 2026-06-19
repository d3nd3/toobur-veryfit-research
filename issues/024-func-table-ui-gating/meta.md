---
id: 024
title: Parse func table (GET 02 02 / 07) and gate GB UI
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [018]
blocks: [013, 015, 019, 023]
---

## Problem

GB exposes prefs (weather, swim sync, dial, reminders) without knowing if **this A200** supports them. VeryFit reads func table on every connect and hides unsupported features.

## Wire

| GET | Payload |
|-----|---------|
| `02 02` | Base func table (~18 bytes bitfields) |
| `02 07` | Extended func table |
| v3 `1A` | v3 func table extension |

## A200 snapshot (from hive vault)

Confirmed bits include: `v3_hr_data`, `v3_swim`, `v3_sleep`, `v3_sync_alarm`, `drink_water_reminder`, `night_auto_brightness`, `multi_dial`, `weather`, `pressure_add_notify_flag_and_mode_03_45`, `automatic_sync_v3_health_data`.

Full 42-table reference: vault `FuncTables.md`, repo `func-tables/function_table.json`.

## GB touchpoints

- Parser for GET `02 02` / `02 07` replies (structure in vault + IDO SDK headers)
- `TooburDeviceSpecificSettingsCustomizer` — hide/disable unsupported prefs (pattern: `CmfWatchProSettingsCustomizer` loops `pref.setVisible(false)` on unsupported sub-keys inside **shared** health XML)
- Store parsed table in device-specific prefs for offline UI
- Gate whole settings tabs when [029](../029-tabbed-device-settings/) lands (e.g. hide Developer sync modes if `automatic_sync_v3_health_data` clear)

## Acceptance criteria

- [x] Connect logs parsed capability flags
- [x] Weather pref hidden if `weather` bit clear
- [x] v3 alarm UI only if `v3_sync_alarm` set
- [x] Document A200 bit snapshot in `docs/external-notes/HIVE-A200-NOTES.md`

## Comments

**Closed 2026-06-19.** `TooburFuncTableCapabilities` parses stored hex (base `protocol_get_func_table` layout + ex byte offsets from A200 capture). Connect logs `TOOBUR func table caps: …`. `TooburDeviceSpecificSettingsCustomizer` hides weather / swim sync / auto-fetch prefs when bits clear; `TooburCoordinator.getAlarmSlotCount` → 0 without `v3_sync_alarm`; `supportsWeather()` gated. Tests: `TooburFuncTableCapabilitiesTest`. HIVE-A200-NOTES + A200-PROTOCOL updated. Next: issue 028 auto-fetch on connect (uses `automatic_sync_v3_health_data`), or 015/016/023 func-table-gated prefs.
