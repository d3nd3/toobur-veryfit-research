---
id: 020
title: Firmware update — OTA 01 + GET 48 status
status: closed
labels: [enhancement]
priority: P3
created: 2026-06-19
depends_on: [010]
blocks: []
---

## Problem

User wants **check for firmware updates** in GB. OTA uses **`0x01`** commands + bulk pipe; status via GET **`02 48`**.

## Wire

| | Role |
|---|------|
| `01 01` | OTA start (bruteforce VALID) |
| `01 02`/`03` | OTA direct / auth (VBUS only) |
| GET `02 48` | Firmware status info |
| Bulk `0x0AF1` | Firmware bytes |

## Captures

- Limited in repo — may need live probe or VeryFit OTA capture

## GB touchpoints

- Device settings: "Check firmware" action
- Parse GET `02 48` on device card (issue 010)
- OTA transfer — high risk; gate behind explicit user confirmation

## Acceptance criteria

- [x] Display firmware status from GET `02 48` when available
- [x] Document OTA flow + `needs-capture` gaps
- [x] Do **not** ship silent OTA without user confirm

## Comments

**Closed 2026-06-19.** `TooburFirmwareStatusPackets` GET `02 48` TX + provisional RX parser; connect + Developer **Query firmware status** action; device card **Firmware OTA** row via `GenericItem`. A200 live probe: no RX (`batch-audit.json`). OTA `01 01`/`02`/`03` + bulk documented in `docs/firmware_ota.md` — transfer not implemented (explicit confirm required for any future OTA). Parser layout `needs-capture` on OTA-capable watch. Next: issue 019 watch faces v3.
