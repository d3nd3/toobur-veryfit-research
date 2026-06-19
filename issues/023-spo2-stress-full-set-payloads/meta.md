---
id: 023
title: SpO₂ & stress SET — full schedule payloads (03 44 / 03 45)
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [002, 018]
blocks: []
---

## Problem

GB only toggles byte 2 (`AA`/`55`) via fixed templates in `TooburHealthSwitchPackets`. VeryFit sends **full schedules**: start/end time, repeat, interval, thresholds, **notifyFlag**. User cannot match app behavior for continuous SpO₂/stress windows.

## Wire

**Stress SET `03 45`** (16 B example):  
`03 45 AA 09 00 12 00 55 3F 3C 00 50 00 01 00 1E`

| Field | Size | Notes |
|-------|------|-------|
| onOff | 1 | `AA`/`55` |
| startHour, startMinute, endHour, endMinute | 4×1 | Schedule window |
| remindOnOff | 1 | Stress reminder |
| repeat | 1 | Weekday bitmask |
| interval | 2 | Minutes |
| highThreshold, notifyFlag, stressThreshold | … | See vault |

**SpO₂ SET `03 44`**: similar + `lowOnOff`, `lowValue`.

Func table: `pressure_add_notify_flag_and_mode_03_45`, `spo2NotifyFlag`.

## References

- Vault: `Toggle Switches Continuous.md`
- Captures: `set_stress_cont_*.txt`
- GB today: `TooburHealthSwitchPackets.java` (templates only)

## GB touchpoints

- Extend `devicesettings_toobur.xml` — schedule + threshold prefs when func table bits set
- Replace template-only builders with parameterized encoder
- Optional GET health switch state (func table `getHealthSwitchState`)

## Acceptance criteria

- [x] TX builder test matches full capture hex (not truncated)
- [x] UI exposes at least start/end schedule for stress; SpO₂ if bit set
- [x] Backward compatible: simple on/off still works

## Comments

**2026-06-19 (closed):** `TooburHealthSwitchPackets` — capture-template builders patch on/off + schedule window; stress 16 B (`set_stress_cont_*.txt`), SpO₂ 10 B (vault). `TooburHealthSwitchPacketsTest` (`set-pressure-03-45`, `set-spo2-03-44`, gb-wired). Health tab: `toobur_*_schedule_start/end` prefs (default 09:00–18:00); `TooburSupport` apply on connect + pref change. Threshold/notify fields kept at capture defaults; defer advanced prefs to func-table follow-up. Next: issue 027 units/profile or 025 per-app notify.
