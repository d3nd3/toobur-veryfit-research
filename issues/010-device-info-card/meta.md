---
id: 010
title: Full device info on GB device card
status: closed
labels: [enhancement]
priority: P1
created: 2026-06-19
depends_on: []
blocks: [018, 020]
---

## Problem

User wants **Bt name, MAC, firmware, resource pack version, last sync time** on device card. GB only shows partial GET `02 01` + battery.

## Wire

| GET | Data |
|-----|------|
| `02 01` | Device id, firmware version (already partial) |
| `02 04` | MAC address |
| `02 A7` | Flash / resource pack info |
| `02 48` | Firmware status (for OTA issue 020) |
| `02 F0` | MTU (already queued) |

## Captures

- `get_device_info.txt`, `get_flashbin_info.txt`, `app_fresh_launch.txt`

## GB touchpoints

- `TooburSupport.initializeDevice()` — queue GETs
- `TooburSupport.onCharacteristicChanged()` — parse replies
- `GBDeviceEventVersionInfo` / custom card fields / `TooburDeviceCardActions` extension
- Store last successful sync timestamp (already have v3 offset prefs)

## UI notes (peer comparison)

- CMF/Xiaomi populate firmware via connect-time version events; Toobur should match that pattern on the **device list card**, not only internal prefs.
- Card action polish (icons, extra slots): [032](../032-device-card-ui-polish/)

## Acceptance criteria

- [x] Device card shows MAC, firmware, resource version when available
- [x] Last sync time reflects last v3 fetch or manual sync
- [x] No crash when GET returns empty (legacy firmware)

## Comments

**2026-06-19 (issue 010 closed):**
- `TooburDeviceInfoPackets` parsers for GET `02 01` / `02 04` / `02 A7`; fixture tests in `TooburDeviceInfoPacketsTest`.
- Connect queues MAC + flash GETs after MTU; card shows FW (`GBDeviceEventVersionInfo`), HW=device id, FW2=resource pack, ADDR=BT MAC, last sync from `lastSyncTimeMillis` after v3 fetch.
- Empty/short GET replies no-op (null parsers); MAC readback only sets ADDR2 when it differs from connection address.
- GET `02 48` firmware status deferred to issue 020.
- Next iteration: issue 018 connect-time sync or issue 022 live probe.
