---
id: 013
title: Weather push — SET 03 2D + 0A 01 forecast data
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [012, 024]
blocks: []
---

## Problem

GB only toggles weather **enable**. Watch needs **`0A 01`** weather payload for watch-face weather. GET **`02 B1`** for switch readback.

## Wire

| | Role |
|---|------|
| SET `03 2D` | Enable (issue 012) |
| CMD `0A 01` | WEATHER_DATA — bulk forecast |
| GET `02 B1` | Weather switch state |

## Captures

- `set_push_weather_*.txt`, `set_dnd_on.txt` (RX `02 B1`)

## GB touchpoints

- Hook Gadgetbridge weather provider → encode VeryFit weather packet
- Queue GET `02 B1` after SET for sync
- Func-table gate: only if weather bit set
- `TooburCoordinator.supportsWeather()` → `true` once push works: [030](../030-coordinator-ui-capability-flags/)
- Weather toggle must call `onSendConfiguration`: [031](../031-settings-customizer-wiring/) (handler currently missing)

## Acceptance criteria

- [x] When GB weather enabled, forecast sent after connect / periodic refresh
- [x] Fixture test for minimal weather TX structure
- [ ] Watch face shows weather (manual QA)

## Comments

**2026-06-19 — closed (agent)**

- `TooburWeatherPackets` + `TooburWeatherPacketsTest`: 18 B `0A 01` matches `set_push_weather_on.txt`; 20 B `0A 02` city name.
- `TooburSupport`: `onSendWeather()`, connect-time push when pref enabled, GET `02 B1` after SET `2D`, weather data on pref toggle.
- `TooburCoordinator.supportsWeather()` → `true`; manifest `weather-push-0a-01` at `gb-wired`.
- `ID115Constants`: `CMD_ID_WEATHER`, `CMD_KEY_GET_WEATHER_SWITCH` (0xB1).

**Decision:** 16 B payload = today (7 B) + 3× future (type/max/min); OWM→IDO type via `WeatherMapper.mapToCmfCondition`. Func-table gating deferred to issue 024.

**Next iteration:** issue 017 watch `07` events or issue 014 goals SET `03 43`.
