---
id: 022
title: Bleak live BLE probe — capture fixtures on demand
status: closed
labels: [enhancement, infrastructure]
priority: P0
created: 2026-06-19
depends_on: []
blocks: [011]
---

## Problem

PRD bootstrap step 3: fill capture gaps without rebuilding the APK. Issue 002 ships logcat extraction but **no live probe**. Several features (MSG verify, GET `02 11`, language) lack A200 fixtures.

## Scope

Python + **Bleak** script targeting Realtek service **`0x0AF0`**, write **`0x0AF6`**, notify **`0x0AF7`** (and bulk **`0x0AF1`/`0x0AF2`** when needed).

## Commands (minimum)

| Probe | TX | Saves fixture for |
|-------|-----|-------------------|
| Battery smoke | `02 05` | Connect sanity |
| Notice status | `02 10` | Issue 025 |
| DND readback | `02 30` | Issue 004 |
| Arbitrary hex | CLI arg | Ad-hoc gaps |

Output: `packetdumps/live/<timestamp>_<label>.txt` (same `TX :` / `RX :` format as logcat).

## References

- PRD § Live BLE probe
- Host: USB BT adapter; watch **disconnected from phone** during session
- [`scripts/extract_logcat_fixtures.py`](../../scripts/extract_logcat_fixtures.py) — companion for fixture import

## Acceptance criteria

- [x] `python scripts/toobur_ble_probe.py --mac XX:XX battery` prints level + writes capture file
- [x] `--tx "02 10"` sends arbitrary GET and logs notify replies
- [x] README section: when to probe vs use logcat
- [x] Documented in issue 002 pipeline as optional stage before fixture commit

## Comments

**2026-06-19 — closed**

- Rewrote `scripts/toobur_ble_probe.py`: presets (`battery`/`notice`/`dnd`), `--tx`, capture writer → `packetdumps/live/`, Bleak + BlueZ D-Bus backends, battery parse/print.
- Added `scripts/test_toobur_ble_probe.py` (offline helpers).
- README: “When to probe vs logcat” section.
- Issue 002 pipeline: live probe is optional stage 3 before fixture commit (see README + `extract_logcat_fixtures.py` header).
- Decision: BlueZ D-Bus fallback when Bleak not installed (Linux dev hosts); `--backend bleak|bluez|auto`.
- Next: issue 011 MSG verify (unblocked) or issue 003 notice alert.
