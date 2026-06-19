---
id: 028
title: Automatic v3 health fetch on connect
status: closed
labels: [enhancement]
priority: P1
created: 2026-06-19
depends_on: [006]
blocks: []
---

## Problem

VeryFit auto-syncs health when func table bit **`automatic_sync_v3_health_data`** is set. GB requires manual fetch — daily charts stay empty unless user remembers to sync.

## Wire

Connect sequence after bind (from `app_fresh_launch.txt`):

1. Func table + user info (issue 018)
2. v3 `05` size probe → v3 `04` per enabled type
3. Respect per-type scope if GB prefs exist

## GB touchpoints

- `TooburSupport.initializeDevice()` — trigger `TooburV3FetchHealthOperation` when bit set
- Honor existing GB auto-fetch / per-type sync prefs if present
- Debounce: skip if last sync < N minutes ago

## Acceptance criteria

- [x] After connect, sleep/SpO₂/stress/sport summary update without manual fetch (when auto bit set)
- [x] Manual fetch still works; no double-fetch storm
- [x] Func-table gate: no auto fetch if bit clear

## Comments

**Closed 2026-06-19.** `TooburConnectAutoFetch` gates on v3 `1A` `automatic_sync_v3_health_data`, `toobur_auto_fetch_enabled`, per-type sync prefs, and debounce (`toobur_auto_fetch_last_ms`). `TooburSupport.maybeTriggerConnectAutoFetch()` runs once per session after v3 func-table reply on `0x0AF2`. `GBAutoFetchReceiver` shares the same gate. Tests: `TooburConnectAutoFetchTest` (`connect-auto-fetch-v3` manifest). Next: issue 029 tabbed settings or 031 weather handler gap.
