# Hive notes — TOOBUR A200 (external vault)

Personal research vault: `/home/dinda/storage/hive/SmartHome/Toobur Veryfit a200`

Canonical merged reference: [`A200-PROTOCOL.md`](../A200-PROTOCOL.md). This file holds **extra detail** from the vault that agents should read when implementing specific features.

## Key vault files

| File | Use for |
|------|---------|
| `0x03 0x30 , 0x02 0x10 , Set Notification + Calls.md` | `protocol_set_notice` struct, 20 B layout |
| `Watch To Phone Messages , State Change.md` | `07 40` notifyType + IDO control evt 551–591 |
| `Toggle Switches Continuous.md` | Full SET `03 44`/`03 45` field layouts |
| `FuncTables.md` | 42-table bit map + **your A200 parsed func table bytes** |
| `HeartRate Sync and Toggle.md` | v3 `09` 12 B unified layout (timestamp, on/off, time range, interval) |
| `Health V3 Sync.md` | day vs count data, start/stop seq examples |
| `Dial WatchFace Hm.md` | v3 `06` = dial list, `08` = set dial |
| `GetDeviceInfo.md` | Example: deviceId=532, firmwareVersion=17 |
| `Phone Tells Watch KeyPress ?.md` | SET `03 E3` volume (deprecated path) |
| `0x03 0x052 UNSURE genssors? Nothing?.md` | SET `03 52` real-time sensor — **unconfirmed** |

## Discoveries not fully in repo captures

### SET `03 30` — `protocol_set_notice` (5 + 15 pad = 20 B)

```c
struct protocol_set_notice {
  uint8_t notify_switch;  // 0x88 in OEM enable example (not 0/1 enum on wire)
  uint8_t notify_item1;
  uint8_t notify_item2;
  uint8_t call_switch;    // 0xAA in OEM example
  uint8_t call_delay;
};
// + 15 bytes 0x00 padding → 20 B total
```

ACK: `notify_switch` echo, `status_code` (often `0x01`), `err_code`.

### `07 40` — watch → phone (evt 577)

After many SETs watch sends `RX : 07 40 …`; phone ACKs `TX : 07 40 …`.

**notifyType** bitmask (IDO GitBook): 1=alarm modified, 2=overheat, 4=brightness (`02 B0`), 8=raise wrist (`02 B1`), 16=refresh DND (`02 30`), 32=volume (deprecated `03 E3`).

**Control events** (phone must handle): 551–555 music, 556–561 camera, **562 answer call**, **563 reject call**, 570/572 find phone, **578 version check**, **579 OTA request**, 580 SMS, etc.

### SET `03 44` / `03 45` — not just on/off

GB templates only flip byte 2 (`AA`/`55`). Full VeryFit payloads include **schedule** (start/end hour/min), **repeat**, **interval**, **thresholds**, **notifyFlag** (see `Toggle Switches Continuous.md`). Func table bit: `pressure_add_notify_flag_and_mode_03_45`.

### v3 HR cmd `09` — unified 12-byte payload (after header)

`UPDATE_TIMESTAMP(4) | ON_OFF(2) 99/AA | TIME_RANGE(4) e.g. 00 00 17 3B | INTERVAL(2) LE | CRC`

VeryFit sends a **reset** packet (`00 01` + all-day range) before ON with interval. See hive HR note for full ON/OFF sequence.

### v3 dial commands

| Cmd | API name |
|-----|----------|
| `06` | Get dial list |
| `08` | Set active dial |
| `07` | Write dial metadata |

### A200 func table snapshot (from vault + live parse)

Parsed from user's watch — gate GB UI via `TooburFuncTableCapabilities`:

| Table | Key offsets (payload bytes) | Notable bits (A200) |
|-------|----------------------------|---------------------|
| Base `02 02` | `ohter` byte 6 bit 7 | `weather` |
| Base `02 02` | `call` byte 4 bit 4 | `v3_function_table` |
| Ex `02 07` | `ex_table_main4` byte 5 | `v3_hr_data` bit 2, `v3_swim` bit 3, `drink_water_reminder` bit 6 |
| Ex `02 07` | `ex_table_main5` byte 6 | `night_auto_brightness` bit 6 |
| Ex `02 07` | `ex_table_main6` byte 9 | `multi_dial` bit 3 |
| Ex `02 07` | `ex_table_main8` byte 12 | `v3_sync_alarm` bit 0, `v3_sleep` bit 7 |
| v3 `1A` | table1 byte 2 bit 6 | `automatic_sync_v3_health_data` |

**GB wiring:** connect logs `TOOBUR func table caps: …`; `TooburDeviceSpecificSettingsCustomizer` hides weather/swim/auto-fetch prefs when bits clear; `getAlarmSlotCount` → 0 without `v3_sync_alarm`; connect + unlock auto-fetch gated by `automatic_sync_v3_health_data` via `TooburConnectAutoFetch`.

Full 42-table bit reference: `FuncTables.md` in vault (also `func-tables/function_table.json` in repo).

### Device info example

`deviceId=532`, `firmwareVersion=17`, `gps_platform=0` (no GPS).

## Maintenance

When vault notes supersede repo docs, update **`A200-PROTOCOL.md`** first, then trim this file.
