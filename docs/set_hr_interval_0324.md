# `set_hr_interval` / SET_HEART_RATE_INTERVAL / `03 24`

Search terms for the same feature:

| Search | Where |
|--------|--------|
| **`set_hr_interval`** | Likely C symbol in VeryFit `protocol_write` / sync config (grep APK or `libido`). |
| **`SET_HEART_RATE_INTERVAL`** | VBUS / SDK name. |
| **`VBUS_EVT_APP_SET_HEART_RATE_INTERVAL`** | Logcat; **evt id `112`** (decimal). |
| **`03 24`** | Wire: SET cmd `0x03`, key **`0x24`**. |
| **`112`** | Numeric evt in `protocol_sync_config.c` request_sync. |

## Repo references

| File | Content |
|------|---------|
| [`bruteforce_results.txt`](../bruteforce_results.txt) | `[VALID] 03 24 - SET_HR_INTERVAL` + vbus 112 |
| [`protocol_util_vbus_evt_to_str.c`](../protocol_util_vbus_evt_to_str.c) | `case 112:` → `VBUS_EVT_APP_SET_HEART_RATE_INTERVAL` |
| [`sub_1ba1d0.c`](../sub_1ba1d0.c) | `case 112` in decompiled switch (evt routing) |
| [`htmlapp/vbus_mapping.json`](../htmlapp/vbus_mapping.json) | eventId **112**, `SET_HEART_RATE_INTERVAL` |
| [`func-tables/function_table.json`](../func-tables/function_table.json) | `level5_hr_interval`, `heart_rate_interval` (capability flags) |
| [`func-tables/ido_func_tables_old.h`](../func-tables/ido_func_tables_old.h) | `IDO_T5_FIVE_HR_INTERVAL`, `IDO_T28_HEART_RATE_INTERVAL`, `IDO_T23_LEVEL5_HR_INTERVAL`, `IDO_T13_NO_SHOW_HR_INTERVAL` |
| [`htmlapp/index.html`](../htmlapp/index.html) | `sendSetHeartRateInterval` → **5 B** `03 24` + burn/aerobic/limit |
| [`htmlapp/toobur-hr-csv.html`](../htmlapp/toobur-hr-csv.html) | Same 5-byte form |

**Note:** [`confirmed-only.html`](../htmlapp/confirmed-only.html) field **`v3_hr_interval`** is **v3 HR mode JSON** (`measurementInterval` for evt **5010** / v3 cmd **0x09**) — **not** the same as SET **`03 24`**.

## Wire formats

### Minimal (angelfit / idowatch HTML)

```
03 24  [burn_fat_bpm]  [aerobic_bpm]  [limit_bpm]
```

3 payload bytes (each 1–255). Described as HR **zone / alert thresholds** (fat burn, aerobic, limit), not sampling period.

### VeryFit full payload (config sync)

From [`packetdumps/logcat/app_fresh_launch.txt`](../packetdumps/logcat/app_fresh_launch.txt) (evt **112**):

```
TX: 03 24  78 8C B4  C8 64  78 8C A0 B4  14  00 00 00 00  17 3B  C8 00
     │      │  │  │   │  │   │  │  │  │   │   │        │   │  │   └── ? (LE 0x00C8 = 200)
     │      │  └──┴──┴── first triple (BPM?): 0x78=120, 0x8C=140, 0xB4=180
     │              second block 78 8C A0 B4 — may be female/max variants or duplicate zones
     │                              0x14 = 20 decimal
     │                                      padding
     │                                              17 3B = often 23:59 (time window end)
RX: 03 24 + 18×00 (20 B total) — ACK / cleared reply shape
```

**Total TX length: 20 bytes** (`03 24` + **18** data bytes = **36 hex** payload after `0324`). Earlier notes said “20 payload bytes” in error. Reverse-engineering the exact struct needs more captures.

## Sync order (VeryFit)

`app_fresh_launch.txt`: **evt 112** at config table **index 24**, before HR mode (**5010**) at index 39. Order: set HR interval (extended `03 24`) → … later → v3 set HR mode.

## Related VBUS (different!)

[`protocol_util_vbus_evt_to_str.c`](../protocol_util_vbus_evt_to_str.c): **`VBUS_EVT_APP_SWITCH_APP_GET_HR_INTERVAL`** — not the same as SET 112; likely a different evt for “get interval” in switch/app UI.
