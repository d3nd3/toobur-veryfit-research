---
id: 027
title: Units & user profile — SET 03 11 + GET 02 22
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [018, 024]
blocks: []
---

## Problem

VeryFit pushes **17-byte SET `03 11`** (units, distance format, etc.) and **SET `03 10`** user info on connect. GB skips both — watch may show wrong units vs GB prefs.

## Wire

| Command | Size | Capture |
|---------|------|---------|
| SET `03 10` | 10 B | `get_sync_health_v3.txt`, `app_fresh_launch.txt` |
| SET `03 11` | 17 B | `app_fresh_launch.txt` |
| GET `02 22` | — | Units readback (VBUS 342) |

## GB touchpoints

- Extend issue 018 connect sequence with builders (not just log raw bytes)
- Map GB user profile (height, weight, gender) + metric/imperial pref → wire fields
- Optional GET `02 22` / `02 23` readback after SET
- **UI:** add `devicesettings_timeformat` (Lefun, ZeTime, C60) under Date/Time tab [029](../029-tabbed-device-settings/)
- **UI:** `devicesettings_language_generic` + `getSupportedLanguageSettings()` (Moyoung pattern) once GET `02 31` confirmed

## Acceptance criteria

- [x] SET `03 11` fixture matches capture for metric + imperial cases
- [x] User info SET when GB profile fields available
- [x] Units follow GB global unit preference

## Comments

**Closed 2026-06-19.** `TooburConnectSyncPackets.buildUserInfo`/`buildUnitsFromGb` wired on connect; imperial + 24h fixture tests; timeformat pref on Generic tab pushes SET `03 11`; profile/unit pref changes push SET `03 10`/`11` via `onSendConfiguration`. GET `02 22` readback + language UI deferred (GET `02 31` unconfirmed). Next: issue 025 per-app notify or 021 camera/sleep period.
