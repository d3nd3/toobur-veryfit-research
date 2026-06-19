---
id: 031
title: Settings customizer — wire all prefs + notify device on change
status: closed
labels: [bug, ui]
priority: P2
created: 2026-06-19
depends_on: []
blocks: [013]
---

## Problem

`TooburDeviceSpecificSettingsCustomizer` only calls `addPreferenceHandlerFor()` for a subset of keys in `devicesettings_toobur.xml`. In Gadgetbridge, **without** a handler, `notifyPreferenceChanged()` never runs → `TooburSupport.onSendConfiguration()` is not called on toggle.

### Confirmed gap

| Pref key | In XML | Handler registered | `onSendConfiguration` case | Effect |
|----------|--------|-------------------|------------------------------|--------|
| `toobur_weather_enabled` | ✅ | ❌ | ✅ | **Bug:** toggle saves locally but does not push SET `2D` |
| `toobur_auto_fetch_enabled` | ✅ | ❌ | — | Phone-only OK if read at fetch time |
| `toobur_auto_fetch_interval_minutes` | ✅ | partial (EditText bind only) | — | Phone-only OK |
| `toobur_live_data_fetch_mode` | ✅ | ❌ | — | Phone-only OK |
| `toobur_v3_sync_*_mode` | ✅ | ❌ | — | Phone-only OK |
| `toobur_v3_health_*` debug | ✅ | ❌ | — | Phone-only OK |

Any future device-pushed pref must follow the handler pattern.

## Reference

- `DeviceSpecificSettingsFragment.addPreferenceHandlerFor()` → `notifyPreferenceChanged(preferenceKey)` → device service
- Peers: `CmfWatchProSettingsCustomizer`, Moyoung handlers via support class

## GB touchpoints

- `TooburDeviceSpecificSettingsCustomizer.customizeSettings()` — add `addPreferenceHandlerFor` for every key that should push to watch
- `TooburSupport.onSendConfiguration()` — ensure switch cases cover all wired keys (weather already has case at `PREF_TOOBUR_WEATHER_ENABLED`)
- Pair with [030](../030-coordinator-ui-capability-flags/) `supportsWeather()` once [013](../013-weather-push-0a-01/) pushes forecast data

## Acceptance criteria

- [x] Toggling `toobur_weather_enabled` triggers `onSendConfiguration` and SET `2D` on device (logcat proof)
- [x] Document in customizer which prefs are phone-only vs device-pushed
- [x] No duplicate handlers for keys already registered

## Comments

<!-- UI audit 2026-06-19: weather handler gap found during peer comparison -->

### 2026-06-19 — closed

- `TooburSupport.DEVICE_PUSHED_PREF_KEYS` — canonical set of prefs that must register handlers and route through `onSendConfiguration` (includes weather → SET `03 2D`).
- `TooburDeviceSpecificSettingsCustomizer.PHONE_ONLY_PREF_KEYS` + class JavaDoc document auto-fetch, v3 sync mode, and debug prefs as phone-only.
- `registerDevicePushedHandlers()` loops the set; `TooburDeviceSpecificSettingsCustomizerTest` guards wiring + SET `2D` bytes via `TooburMusicWeatherSwitchPackets`.
- Next: issue 030 coordinator capability flags or 029 tabbed settings layout.
