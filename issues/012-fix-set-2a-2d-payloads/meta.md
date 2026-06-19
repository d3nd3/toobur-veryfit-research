---
id: 012
title: Fix SET 03 2A music and 03 2D weather switch payloads
status: closed
labels: [enhancement, bugfix]
priority: P2
created: 2026-06-19
depends_on: [002]
blocks: [013]
---

## Problem

GB sends **3-byte** music and **4-byte** weather switches. A200 expects **4 B** and **6 B** respectively.

## Wire

| Key | A200 example |
|-----|----------------|
| `03 2A` | `03 2A AA 55` (4 B) |
| `03 2D` | `03 2D AA 00 00 00` (6 B) |

## Captures

- `set_music_on.txt`, `set_push_weather_on.txt`

## GB touchpoints

- `TooburSupport.applyMusicSwitchFromPrefs()`
- `TooburSupport.applyWeatherSwitchFromPrefs()`

## Acceptance criteria

- [x] TX builder tests match captures
- [x] Toggles still work on device after fix

## Comments

**2026-06-19 — closed**

- `TooburMusicWeatherSwitchPackets` + `TooburMusicWeatherSwitchPacketsTest`: music `AA 55`/`55 55` (4 B), weather `AA 00 00 00`/`55 00 00 00` (6 B); fixes wrong 3 B music and 4 B weather with `0/1` on byte.
- `TooburSupport` uses builders in connect + `onSendConfiguration`.
- Manifest: `set-music-03-2a`, `set-weather-03-2d` at `gb-wired`.

**Decision:** second music byte is always `0x55` per capture; weather uses `AA`/`55` not `1`/`0`.

**Next iteration:** issue 013 weather `0A 01` forecast push (unblocked) or issue 017 watch `07` events.
