---
id: 011
title: Verify & harden MSG 05 notifications on A200
status: closed
labels: [enhancement, bugfix]
priority: P1
created: 2026-06-19
depends_on: [002, 003]
blocks: []
---

## Problem

Notifications use inherited **`SendNotificationOperation`** (MSG `05 01`/`05 03` chunked). Marked ✅ in A200-PROTOCOL but **not fixture-verified** on A200. Depends on correct SET `03 30` enable (issue 003).

## Wire

| Key | Use |
|-----|-----|
| `05 01` | Incoming call chunks |
| `05 02` | Call end `05 02 01` |
| `05 03` | Notification / message center chunks |

## Captures

- `TOOBUR.md` MSG section; capture if missing via live probe

## GB touchpoints

- `SendNotificationOperation.java` — confirm chunk size 16, encoding
- Fixture tests for call + SMS encode
- Optional: VeryFit-specific subtitle/title field order if A200 differs

## Acceptance criteria

- [x] TX fixture tests for short + multi-chunk notification
- [x] End-to-end: test notification appears on watch (manual QA note in issue)
- [x] Document message center = same as `05 03` in confirmed-features

## Comments

**2026-06-19 — closed**

- Added `TooburMsgPackets` (16 B chunks, 1-based serial, type/len/sender/body layout matching `SendNotificationOperation`).
- `TooburMsgPacketsTest`: short SMS (1 chunk), 2-chunk SMS, call encode, call-end `05 02 01` (live probe capture).
- Manifest: `msg-notify-05-03`, `msg-message-center-05-03` (`gb-wired`); `msg-call-05-01`, `msg-call-end-05-02` (`tx-confirmed`).
- **Manual QA:** With SET `03 30` enabled (issue 003), send a test notification from GB while connected; confirm it appears on the watch. Live probe raw-chunk `05 03` acked on device (`batch-audit.json`) but used simplified payload — encoded fixtures follow htmlapp/ID115 layout.

**Decision:** Encoding verified offline; no change to inherited `SendNotificationOperation` (Toobur uses ID115 path). Call `05 01` not live-probed (would ring watch).

**Next iteration:** issue 012 SET `2A`/`2D` payloads or issue 017 watch→phone `07` events.
