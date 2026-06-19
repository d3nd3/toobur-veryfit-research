---
id: 025
title: Per-app notification switches — GET 02 10 + SET notice sub-items
status: closed
labels: [enhancement]
priority: P2
created: 2026-06-19
depends_on: [003, 024]
blocks: []
---

## Problem

VeryFit `protocol_set_notice` has **notify_item1**, **notify_item2** for per-app/sub-switch config. GB only sends master call/notice bytes. User wants granular control (SMS, WhatsApp, etc.) matching func table notify bits.

## Wire

| | Role |
|---|------|
| SET `03 30` byte 0 | `notify_switch` (mode / master — `0x88` in captures) |
| SET `03 30` bytes 1–2 | `notify_item1`, `notify_item2` |
| SET `03 30` byte 3 | `call_switch` (`0xAA`) |
| GET `02 10` | Notice status (bruteforce VALID) |
| Func table | Per-app bits: message, whatsapp, telegram, … (tables 8–10, 32–33) |

## References

- Vault: `0x03 0x30 , 0x02 0x10 , Set Notification + Calls.md`
- [`A200-PROTOCOL.md`](../../A200-PROTOCOL.md) SET `03 30`
- Issue [003](../003-fix-set-03-30-notice-alert/) (20 B base packet)

## GB touchpoints

- Map Gadgetbridge app notification prefs → notify_item bitfields
- GET `02 10` on connect for readback
- Depends on func table gating ([024](../024-func-table-ui-gating/))

## Acceptance criteria

- [x] Master + at least 3 app channels configurable
- [x] Fixture test for enable/disable hex with non-zero item bytes
- [x] Integrates with GB transliteration / app filter prefs where possible

## Comments

**2026-06-19 — closed**

- `TooburNoticeAlertPackets`: `buildA200Notice` with item1/item2, `buildGetNoticeStatus`, `parseGetNoticeStatus`, `buildFromPrefs` (SMS/WeChat/WhatsApp bit map from IDO `IDOV2NoticeItemInfo`).
- Notifications tab: master `toobur_notify_apps_enabled` + per-app toggles; func-table gating via `isNotifySms/Wechat/Whatsapp`.
- `TooburSupport`: connect/onSendConfiguration pushes full 20 B SET; GET `02 10` queued after SET; readback logged.
- Tests: `set-notice-items-03-30`, `get-notice-02-10` in `TooburNoticeAlertPacketsTest`.
- Deferred: Telegram (notify_item3 — beyond A200 5-field struct), pref sync from GET readback, GB per-app blacklist auto-mapping.
