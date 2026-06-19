---
id: 026
title: v3 HR continuous — full cmd 09 schedule payloads
status: closed
labels: [enhancement]
priority: P1
created: 2026-06-19
depends_on: [002]
blocks: [007]
---

## Problem

GB toggles continuous HR via v3 **`09`** but uses simplified payloads. VeryFit sends a **reset** packet (`ON_OFF 00 01` + all-day time range) before enabling with **interval + schedule** (12 B unified layout). Legacy SET **`03 25`** still sent — redundant on A200.

## Wire

v3 cmd **`09`** payload (after frame header):

`UPDATE_TIMESTAMP(4) | ON_OFF(2) 99/AA/00 01 | TIME_RANGE(4) | INTERVAL(2) LE | CRC`

| Step | Meaning |
|------|---------|
| Reset | `00 01` + default window before ON |
| ON | `AA` + user window + interval minutes |
| OFF | `55` |

Hive sequence: vault `HeartRate Sync and Toggle.md`.

## Captures

- `set_hr_cont_*.txt` if present; else probe via issue 022

## GB touchpoints

- `TooburV3HrPackets.java` — replace minimal templates
- `TooburSupport` / device settings — interval + optional smart mode
- Stop sending legacy SET `03 25` on A200 after v3 path confirmed

## Acceptance criteria

- [x] TX fixture: OFF → reset → ON sequence matches capture or hive reference
- [x] Interval pref (e.g. 5 / 10 / 30 min) reflected in wire bytes
- [x] Legacy `03 25` gated off for Toobur A200 coordinator
- [x] Links to issue 007 (HR-day chart uses same measurement window)

## Comments

**Closed 2026-06-19.** `TooburV3HrPackets`: `buildHrMode` (`99`/`AA` + interval), `buildHrSchedule` (all-day `00:00`–`23:59`), `buildHrReset` (bind prelude), `buildHrApplySequence` (OFF: 2 pkts; ON: reset+mode+schedule). `TooburV3HrPacketsTest` fixtures from `set_hr_cont_state_on/off.txt` + bind reset. `TooburSupport.applyContinuousHrV3` sends 2–3 frames with 150 ms gap; legacy SET `03 25` never sent. Interval pref unchanged on Health tab. Next: issue 023 SpO₂/stress full schedules or 027 units/user profile.
