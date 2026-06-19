---
id: 017
title: Watch-initiated BLE events — handle 07 40 and call actions
status: closed
labels: [enhancement]
priority: P1
created: 2026-06-19
depends_on: []
blocks: []
---

## Problem

Watch sends **`07 40`** data-update notifies and control events (music, **answer/reject call**, find phone, OTA check) via **`0x07`**. GB ignores watch→phone direction — user cannot answer calls from the band or respond to find-phone from watch.

## Wire

| Direction | Example |
|-----------|---------|
| Watch → phone | `RX : 07 40 00 00 10 00 …` (evt **577**) |
| Phone → watch ACK | `TX : 07 40 00 00 10 00 …` |

**notifyType** bitmask on `07 40`:

| Bit | Readback |
|-----|----------|
| 4 (16) | GET `02 30` after DND SET |
| 3 (8) | GET `02 B1` after wrist SET |
| 2 (4) | GET `02 B0` after brightness |

**Control events** (IDO evt 551–591):

| Evt | Action |
|-----|--------|
| 551–555 | Music play/pause/prev/next |
| **562** | **Answer phone call** |
| **563** | **Reject phone call** |
| 570/572 | Find phone start/stop |
| 578 | Version check |
| 579 | OTA request |

Also: `07 01` photo preview, `07 03` SOS (VBUS).

## References

- Vault: `Watch To Phone Messages , State Change.md`
- [`docs/external-notes/HIVE-A200-NOTES.md`](../../docs/external-notes/HIVE-A200-NOTES.md)
- Captures: `set_dnd_on.txt`, `set_hand_gesture_wake_on.txt`

## GB touchpoints

- `TooburSupport.onCharacteristicChanged()` — dispatch `07 xx` on `0x0AF7`
- Always ACK `07 40` per capture pattern; optional GET readbacks by notifyType
- Android: `MediaSession`, telecom/call APIs, find-phone intent

## Acceptance criteria

- [x] GB ACKs `07 40` without breaking connection
- [x] At least **music prev/next** OR **call reject** wired to Android
- [x] notifyType `16` triggers GET `02 30` after DND SET (mirror VeryFit)
- [x] Event table documented in confirmed-features

## Comments

**2026-06-19 — Issue 017 closed**

- `TooburBleEventPackets` + `TooburBleEventPacketsTest`: ACK `07 40` (18 B), notifyType parse, GET readback keys (4→`02 B0`, 8→`02 B1`, 16→`02 30`).
- `TooburSupport.handleBleControlFromWatch`: queues ACK + readbacks; dispatches `07 01` music next/prev + call accept/reject and `07 02` find-phone via GB device events.
- Music/call wire layout from IDO SDK `protocol_exec_ble_control` (cmd1 = evt − 550); no live music/call capture — manual QA on band.
- Manifest: `ble-notify-07-40`, `ble-control-music-next-07-01`, `ble-control-call-reject-07-01`.
- Next: issue 018 connect-time func table sync.
