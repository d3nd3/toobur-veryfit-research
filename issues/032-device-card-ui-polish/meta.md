---
id: 032
title: Device card UI polish — icons, quick toggles, camera shortcut
status: closed
labels: [enhancement, ui]
priority: P2
created: 2026-06-19
depends_on: [010]
blocks: []
---

## Problem

`TooburDeviceCardActions` is already ahead of ID115/FitPro peers (HR, SpO₂, stress, auto-activity on the device list card). Several polish gaps remain vs other Gadgetbridge drivers and vs VeryFit’s high-frequency toggles.

## Current state

- Four card slots: HR, SpO₂, stress, auto-activity (`TooburDeviceCardActions.java`)
- Stress icon: `ic_activity_unknown` (weak)
- SpO₂ icon: `ic_activity_graphs` (not SpO₂-specific)
- No quick toggle for **DND** or **raise-to-wake** (both wired in settings)
- No **camera** card action (FitPro/C60 use `DeviceCardAction.CameraAction`; wire in [021](../021-extra-app-controls/))
- Device card metadata thin vs [010](../010-device-info-card/) (MAC, firmware, resource pack, last sync)

## Ideas (prioritized)

| Item | Peer pattern | Notes |
|------|--------------|-------|
| Better icons | CMF uses themed health icons | Use `ic_heartrate`, dedicated SpO₂/stress drawables if present |
| DND quick toggle | — | Tap cycles off/on; label shows schedule summary or On/Off |
| Raise-to-wake quick toggle | — | Mirrors `toobur_raise_to_wake` pref |
| Camera shortcut | `FitProDeviceCoordinator.getCustomActions()` | APP `06 02` via [021](../021-extra-app-controls/) |
| Card metadata rows | Standard `GBDevice` firmware/battery fields | Extend [010](../010-device-info-card/) |
| `isVisible()` guard | `UltrahumanDeviceCardAction` | Hide actions until `INITIALIZED` |

Card has **four slots** in `device_itemv2` layout — adding DND/camera may require cycling labels, long-press for more, or replacing lowest-priority slot.

## GB touchpoints

- `TooburDeviceCardActions.java` — new actions + icon fixes
- `TooburCoordinator.getCustomActions()`
- Optional strings in `strings.xml` for new card labels
- [010](../010-device-info-card/) for firmware/MAC/last-sync on card body (not action chips)

## Acceptance criteria

- [x] SpO₂ and stress card actions use appropriate icons (not generic activity)
- [x] At least one of: DND card toggle, raise-to-wake card toggle, or camera card action — with UX note if slot limit blocks all three
- [x] Card actions no-op gracefully when device not connected
- [x] [010](../010-device-info-card/) acceptance criteria still met if card layout changes

## Comments

<!-- UI audit 2026-06-19 -->

**2026-06-19 (issue 032 closed):**
- SpO₂ → `ic_spo2`, stress → `ic_stress`; DND quick toggle replaces auto-activity slot (4-slot `device_itemv2` limit — auto-activity presets remain in Health settings; raise-to-wake + camera deferred to 021).
- `InitializedCardAction` base: `isVisible` at INITIALIZED; `onClick` no-op when disconnected.
- DND label shows schedule window when enabled (e.g. `22:30–06:45`).
- `TooburDeviceCardActionsTest` covers icons, visibility, DND label, disconnected guard.
