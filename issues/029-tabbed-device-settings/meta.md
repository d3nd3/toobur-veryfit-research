---
id: 029
title: Tabbed device settings — DeviceSpecificSettingsScreen layout
status: closed
labels: [enhancement, ui]
priority: P2
created: 2026-06-19
depends_on: []
blocks: []
---

## Problem

All TOOBUR prefs live in one flat `devicesettings_toobur.xml` screen. Peer drivers (**CMF Watch Pro**, **Xiaomi**, **ZeTime**, **Moyoung**) split settings into tabbed root screens (`DeviceSpecificSettings` + `DeviceSpecificSettingsScreen`), which keeps everyday toggles separate from developer/debug options.

Today users see v3 offset probes, force-full sync, and per-type sync mode lists mixed with DND, HR, and call-alert toggles.

## Reference implementations

| Driver | Pattern |
|--------|---------|
| `CmfWatchProCoordinator.getDeviceSpecificSettings()` | DATE_TIME, DISPLAY, HEALTH, CALLS_AND_NOTIFICATIONS, CONTACTS |
| `ZeTimeCoordinator` | GENERIC, DATE_TIME, DISPLAY, HEALTH, NOTIFICATIONS, CALENDAR, ACTIVITY_INFO, **DEVELOPER** |
| `AbstractMoyoungDeviceCoordinator` | GENERIC + HEALTH tabs |

## Proposed Toobur layout

| Tab | Contents (move from current XML) |
|-----|----------------------------------|
| **Device** | Bind/unbind, music, call alert, transliteration (keep global) |
| **Display** | Raise-to-wake (`toobur_raise_to_wake`); later auto-brightness [016](../016-auto-brightness-set-32/) |
| **Health** | HR continuous + interval, SpO₂, stress, auto-activity preset |
| **DND** | `toobur_dnd_*` (or fold into Notifications once [004](../004-fix-set-03-29-dnd-schedule/) stable) |
| **Sync** | Auto-fetch enable + interval, live-data fetch mode |
| **Developer** | All `toobur_v3_sync_*_mode`, sport offset probe, force-full fetch |

Wear location + screen orientation stay as separate included XML (current pattern).

## GB touchpoints

- Replace `TooburCoordinator.getSupportedDeviceSpecificSettings(int[])` with `getDeviceSpecificSettings(GBDevice)` returning `DeviceSpecificSettings`
- Split `devicesettings_toobur.xml` into `devicesettings_toobur_device.xml`, `_health.xml`, `_sync.xml`, `_developer.xml` (or equivalent)
- `TooburDeviceSpecificSettingsCustomizer` — no behaviour change; handlers stay the same

## Acceptance criteria

- [x] Device settings open with multiple top-level tabs (not one long scroll)
- [x] v3 debug / sync-mode prefs only under Developer (or Sync + Developer split)
- [x] Existing pref keys unchanged (no migration)
- [x] Func-table gating [024](../024-func-table-ui-gating/) can hide whole tabs or prefs per tab

## Comments

<!-- UI audit 2026-06-19: compared against CMF/ZeTime/Moyoung coordinators -->

**2026-06-19 — closed.** `TooburCoordinator.getDeviceSpecificSettings()`: wear location + orientation flat roots; tabbed Generic (device + transliteration), Display, Health, Notifications (DND), Connection (sync), Developer (v3 sync modes + probes). Split XML: `devicesettings_toobur_{device,display,health,dnd,sync,developer}.xml`; removed monolithic `devicesettings_toobur.xml`. `TooburCoordinatorTest.deviceSettings_useTabbedRootScreens`. Customizer unchanged — per-pref func-table gating still works.
