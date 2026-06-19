---
id: 003
title: Fix SET 03 30 call/notification alert (20-byte A200 payload)
status: closed
labels: [enhancement, bugfix]
priority: P0
created: 2026-06-19
depends_on: [002]
blocks: []
---

## Problem

GB sends legacy **5-byte** SET `03 30`. A200 expects **20-byte** call/notice alert per VeryFit captures.

## Wire

| | Bytes |
|---|--------|
| **TX (A200)** | `03 30 88 00 00 AA 00 00 00 00 00 00 00 00 00 00 00 00 00 00` (enable example) |
| **Struct** | `notify_switch`, `notify_item1`, `notify_item2`, `call_switch`, `call_delay` + 15× `00` pad |
| **TX (GB today)** | `03 30 [1/0] 00 00 [1/0] 03` — wrong |
| **GET readback** | `02 10` notice status |
| **VBUS** | 111 SET_NOTICE |
| **GATT** | Write `0x0AF6` |

Per-app bits: see issue [025](../025-per-app-notification-switches/) + [`A200-PROTOCOL.md` § SET 03 30](../../A200-PROTOCOL.md#set-03-30--protocol_set_notice).

## Captures

- `packetdumps/logcat/app_fresh_launch.txt`
- [`A200-PROTOCOL.md` § SET alerts](../../A200-PROTOCOL.md#set--0x03--key)

## GB touchpoints

- `TooburSupport.applyCallAlertFromPrefs()`
- `devicesettings_toobur.xml` — `toobur_call_alert_enabled`
- Optional: split SMS vs call sub-switches if capture supports

## Acceptance criteria

- [x] TX builder test matches capture hex for on/off
- [x] Toggle in device settings sends 20-byte packet on connect + on change
- [x] Entry in `docs/confirmed-features.md` at `gb-wired`

## Comments

**2026-06-19 — closed**

- Added `TooburNoticeAlertPackets.buildA200CallAlert()` (20 B `protocol_set_notice` + pad; enable `88/AA`, disable `88/55`).
- `TooburSupport.applyCallAlertFromPrefs()` now uses the builder on connect and pref change.
- `TooburNoticeAlertPacketsTest` + manifest `set-notice-03-30` at `gb-wired`.
- Per-app `notify_item1`/`notify_item2` deferred to issue 025.
