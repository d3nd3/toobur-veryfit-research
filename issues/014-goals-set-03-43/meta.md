---
id: 014
title: Goals — SET 03 03 / 04 / 43 (steps, sleep, calorie+distance)
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [002]
blocks: []
---

## Problem

Only step goal (SET `03 03`) is wired via ID115. Missing **sleep goal** (`03 04`) and **calorie+distance goals** (`03 43`, 20 B).

## Wire

| Key | VBUS | Capture |
|-----|------|---------|
| `03 03` | 105 sport goal | ✅ GB `setGoal()` |
| `03 04` | 106 sleep goal | — |
| `03 43` | 161 calorie/distance | `app_fresh_launch.txt` |

## GB touchpoints

- Extend GB prefs / activity goal UI where applicable
- `TooburSupport` or ID115 goal setters on connect
- Reuse GB global step goal + optional `devicesettings_goal_notification` (C60 pattern) for watch celebration on goal hit

## Acceptance criteria

- [x] SET `03 43` builder test matches capture
- [x] Goals pushed on connect or when user changes GB activity goals
- [x] Sleep goal exposed if GB has sleep goal pref

## Comments

**Closed 2026-06-19:** `TooburGoalPackets` + `TooburGoalPacketsTest` (17 B sport, 4 B sleep, 20 B calorie+distance). `TooburSupport.setGoal()` override pushes all three on connect; `onSendConfiguration` handles `fitness_goal`, calories, distance, sleep duration, goal-notification prefs. Manifest: `set-sport-goal-03-03`, `set-sleep-goal-03-04`, `set-calorie-distance-03-43` at `gb-wired`.

**Decision:** A200 sport goal is 17 B (not ID115 9 B); `03 43` tail uses VeryFit bind constants (`1800` walk time, `250`/`0E`/`06`/`0C` schedule fields) until issue 023/027 expose schedule UI.

**Next iteration:** issue 017 watch `07` events or issue 018 connect-time func-table sync.
