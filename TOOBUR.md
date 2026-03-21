Most of these brands (Toobur, Runlio, Biggerfive) are essentially "skins" for hardware designed and manufactured by a single major OEM: **Shenzhen DO Intelligent Technology Co., Ltd** (commonly known as **IDO**).


Because these devices prioritize low power consumption over high-speed processing, they don't use "mobile" chips like those from Qualcomm. Instead, they use highly integrated **Microcontroller Units (MCUs)**.


While the exact chip can vary by model year, the "VeryFit" ecosystem predominantly uses two silicon suppliers:

- **Nordic Semiconductor:** The **nRF52 series** (like the nRF52832 or nRF52840) is the "gold standard" for this category. These SoCs are famous for their ultra-low-power Bluetooth LE (Low Energy) performance.
    
- **Realtek:** In ultra-budget models (like the Runlio or older Biggerfive models), you’ll often find **Realtek RTL8762 series** chips. These are cheaper alternatives to Nordic but offer similar Bluetooth 5.0/5.1 stability.
    
- **Goodix:** Some newer models with "Bluetooth Calling" features use Goodix chips, which are optimized for handling both high-fidelity audio and low-energy sensor data simultaneously.


### 2. The Bluetooth "Pipeline"

The "VeryFit" pipeline is a standardized communication bridge designed by IDO to allow thousands of different unbranded watches to talk to a single app.

- **The Protocol:** They use **GATT (Generic Attribute Profile)** over Bluetooth Low Energy. The watch acts as a "Server" containing data (attributes) like heart rate or step count, and the VeryFit app acts as the "Client" that requests that data.
    
- **Data Syncing:** Instead of a constant stream, the watch stores data in its local flash memory in small "packets." When you open the app, it triggers a "Sync" command. The MCU packages the stored sensor data into a compressed binary format and sends it over the BLE link.
    
- **Command Pipe:** The pipeline also works in reverse for notifications. When your phone gets a text, the app sends a specific hex code to the watch’s "Notification Characteristic," which the MCU then parses to display text on the screen.



Nordic nRF52840 or Realtek RTL8762

---

### The Verdict: It’s a Realtek SoC

The UUID **0x0AF0** is the proprietary service used by **Realtek Semiconductor** for their Bluetooth Low Energy (BLE) stack, specifically for their "OTA" (Over-the-Air) firmware update process.

- **Chip Family:** You are likely looking at a **Realtek RTL8762 series** chip (most commonly the RTL8762C or RTL8762D).
    
- **Why it's there:** Realtek dominates the budget fitness tracker market because their "SDK" (Software Development Kit) is extremely easy for manufacturers like **IDO (VeryFit)** to implement quickly.


### A Quick Experiment

If you want to see the Realtek "pipeline" in action:

1. In **nRF Connect**, tap on the **0x0AF0** service to expand it.
    
2. Look for a **Characteristic** (usually a long UUID) with the properties **"Write"** or **"Notify"**.
    
3. This is the "tunnel" the VeryFit app uses to push new watch faces or firmware updates to your wrist.

The services you’ve pulled from nRF Connect tell a very specific story. While **0x1800** (Generic Access) and **0x1801** (Generic Attribute) are standard Bluetooth "housekeeping" services found on almost every device

---

#### 1. The Command Center (0x0AF6 & 0x0AF1)

- **Properties:** READ, WRITE, WRITE NO RESPONSE.
    
- **Purpose:** These are the **Inbound Pipes**. When you change a setting in the app (like turning on "Lift to Wake" or setting an alarm), the app writes a hex command to these characteristics.
    
- **Why two?** Usually, one is for "Control Commands" (settings) and the other is for "Bulk Data" (like pushing a new Watch Face file, which requires "Write No Response" for higher speed).

#### 2. The Heartbeat / Live Data (0x0AF7)

- **Properties:** NOTIFY, READ.
    
- **Descriptor (0x2902):** Notifications Enabled.
    
- **Purpose:** This is the **Active Stream**. When this is "Enabled," the watch doesn't wait for the app to ask for data; it "pushes" updates instantly. This is where your **Live Heart Rate** and **Step Count** increments are sent to the phone in real-time while the app is open.

#### 3. The Health Log / Sync (0x0AF2)

- **Properties:** NOTIFY, READ.
    
- **Purpose:** This is the **History Pipe**. When you pull down to sync the app in the morning, the watch uses this characteristic to dump the last 24 hours of sleep and SpO2 data that was stored in its internal flash memory.

---

### Technical Specs of your SoC (Realtek RTL8762D)

Since we've narrowed it down to this chip family, here is what is actually running on your wrist:

- **Processor:** ARM Cortex-M4F (Running at roughly **40MHz to 90MHz**).
    
- **RAM:** Approx. **192KB to 256KB** (Yes, Kilobytes! It’s incredibly efficient).
    
- **Flash:** Usually **64MB to 128MB** of external SPI flash for those watch faces and health logs.
    
- **Bluetooth:** Version **5.0/5.1** Low Energy.

---

### Fun Fact: Why the "0x2902" Descriptor matters

The `0x2902` you see is the **Client Characteristic Configuration Descriptor (CCCD)**. It acts like a light switch.

- If the value is `0x0000`, the watch stays silent to save battery.
    
- When the VeryFit app connects, it writes `0x0100` to that "switch," which tells the Realtek chip: _"Okay, start broadcasting the sensor data now."_

---

| **Feature**        | **Bangle.js 1** | **Bangle.js 2**     | **Realtek RTL8762D**    |
| ------------------ | --------------- | ------------------- | ----------------------- |
| **Core Processor** | Nordic nRF52832 | **Nordic nRF52840** | **Realtek RTL8762D**    |
| **Architecture**   | ARM Cortex-M4   | ARM Cortex-M4F      | ARM Cortex-M4F          |
| **Clock Speed**    | 64 MHz          | 64 MHz              | **Up to 90 MHz**        |
| **On-Chip RAM**    | 64 KB           | **256 KB**          | **160 KB - 192 KB**     |
| **On-Chip Flash**  | 512 KB          | 1 MB                | **Up to 2 MB** (varies) |
| **External Flash** | 4 MB (SPI)      | 8 MB (QSPI)         | Typically 64MB - 128MB* |
| **Bluetooth**      | 4.2             | 5.0                 | **5.1**                 |

---

Capture correction:
- `new_setup.json` shows that the `03:30:55:01:00` packet is a **watch notification on 0x0AF7**, not a host write. It matches the legacy `protocol_set_notice_ack` shape (`notify_switch=0x55`, `status=1`, `err=0`).
- So the earlier **`0x55 = 85 bpm`** guess was wrong: in this capture, generic `0x03` packets are **setup/status replies**, not evidence of live heart-rate streaming.

### Summary

| Item | Finding |
|------|--------|
| Protocol | IDO/Realtek 0x0AF0 service; host writes use 0x0AF6 and watch notifications use 0x0AF7. VeryFit also enables 0x0AF2 notifications, but 0x0AF2 stays silent in this trace. |
| GPS | None (gps_platform: 0). |
| Activity | Reply received but version 0 / all zeros → no stored activity in the watch at capture time. |
| `0x03` packets | In this trace they are setup/status replies (for example `03:30:55:01:00`), not proof of live HR. |
| Reset / wipe | No explicit `03:27` (factory defaults) or `F0:01` (reboot) command appears in the capture. |
| Connection | VeryFit does more setup than idowatch’s minimal `GET info → activity` flow, but the extra packets are configuration/status traffic rather than a visible reset command. |

### TOOBUR A200 (and compatible) vs older angelfit protocol

The following summarizes how **TOOBUR A200** (and firmware that matches the VeryFit logcat dumps in `logcat_dumps/`) differs from the **older angelfit** protocol. The same GATT layout (0x0AF0, write 0x0AF6, notify 0x0AF7, bulk 0x0AF1/0x0AF2) is used; the differences are in command set, payload sizes, and use of the **v3 (0x33) protocol**.

| Aspect | Older angelfit | TOOBUR A200 / VeryFit dumps |
|--------|----------------|-----------------------------|
| **Notice / call alert** | SET 0x03 0x30 with **5-byte** payload (notify_switch, call_switch, call_delay, etc.). | VeryFit uses **20-byte** SET 0x30: **enable** = `03 30 88 00 00 AA 00 00 00 00 00 00 00 00 00 00 00 00 00 00` (full 20 B in **app_fresh_launch.txt** line 880); reply `03 30 88 01 00` (line 882). **Disable** = no app→watch capture; use **`03 30 88 00 00 55`** + 14 zero bytes (0x55 = off, same as Music/DND; the watch sends `RX 03 30 55 01 00...` when reporting off — line 36). Do not use 0x88 in the 5th byte for off; 0x88 here is the first payload byte (subtype), not on/off. |
| **Heart rate on/off** | SET 0x03 0x25 (mode 0x55/0x88/0xAA); SET 0x24 (interval); SET 0x52 (real-time sensor). | **Continuous HR / Stress** toggles: **SET 0x45** (on: `03 45 AA ...`, off: `03 45 55 ...`) and **v3 cmd 0x09** (get/set HR mode state). The **set_hr_cont_state** dumps show **v3 cmd 0x09 only** (no SET 0x45 in that flow); **set_stress_cont_*** and **healthdata_toggles** show SET 0x45 + v3 0x09. Legacy 0x25/0x52 are not sent by VeryFit for those toggles; GET 0x02 0x08 is sent in a 4× burst after 0x45 changes. See `logcat_dumps/set_hr_cont_state_*.txt`, `set_stress_cont_*.txt`, `get_hr_cont_state.txt`. |
| **Alarms** | SET 0x03 0x02 (legacy) with 7-byte payload per alarm. | **Alarms via v3**: GET alarm = v3 cmd **0x0F** (`33 DA AD DA AD 01 0C 00 0F 00 24 01 00 28 18`). **SET alarms (and sport order)** = v3 cmd **0x0E** (VBUS_EVT_FUNC_V3_SPORT_SORT evt 5017): one 355-byte packet with **0x0A = 10 alarm slots**. Payload after v3 header: alarm count (0x0A), then per-alarm block: alarm id, on/off (0x55=off, 0xAA=on), **hour, minute** (e.g. `04 19` = 4:19 AM), then repeat/type/etc. See `logcat_dumps/set_alarms_and_sports.txt` — bytes `04 19` in the hex are the time of one alarm. Legacy SET 0x02 may still be used on some firmware. |
| **Do not disturb** | SET 0x03 0x29 (same key). | Same key; A200 uses **14-byte payload** after cmd+key (not the legacy 5-byte form). Example on: `03 29 AA 17 00 07 00 02 FE 55 17 00 07 00 00 00`; off: first payload byte `55`. After SET, VeryFit sends **GET 0x02 0x30** (**VBUS_EVT_APP_GET_DO_NOT_DISTURB**) for DND read. The **02 30** reply’s **third byte** is DND state: **0x55** = off, **0xAA** = on (set_dnd_off.txt line 28: `RX : 02 30 55 17 00 07 00...`; set_dnd_on.txt: `02 30 AA 17 00 07 00...`). See `logcat_dumps/set_dnd_on.txt`, `set_dnd_off.txt`. |
| **Device / flash** | GET 0x02 0x01 (device info), 0x02 0x02 (func table), etc. | Adds **GET 0x02 0xA7** (flashbin info; reply e.g. `02 A7 00 01 01 78 56 34 12`). GET 0x02 **0x30** = **VBUS_EVT_APP_GET_DO_NOT_DISTURB** (DND read; evt **326** in logcat). VeryFit sends it after SET DND and in config-sync. Reply format: `02 30 [byte2] 17 00 07 00...` — **byte 2** = **DND state**: **0x55** = off, **0xAA** = on (set_dnd_off.txt line 28: `02 30 55 17 00 07 00 02 FE 55...`; set_dnd_on: `02 30 AA...`). Rest of payload (17 00 07 00 etc.) not fully confirmed. GET 0x02 **0xB1** = **GET_WEATHER_SWITCH** (evt **316**); reply includes weather on/off state. See `logcat_dumps/set_dnd_on.txt`, `set_dnd_off.txt`, `set_push_weather_*.txt`, `app_fresh_launch.txt`. |
| **Screen brightness** | Not in angelfit command table. | **SET 0x03 0x32** (VBUS_EVT_APP_SET_SCREEN_BRIGHTNESS): 12-byte packet; 6th byte (1-based) = **0x01** (auto off) or **0x03** (auto on 19:00–06:00). Example: `03 32 28 01 00 01 13 00 06 00 00 05` (off), `03 32 28 01 00 03 13 00 06 00 00 05` (on). See `logcat_dumps/set_auto_brightness_off.txt`, `set_auto_brightness_on_19pm_to_6am.txt`. |
| **Hand gesture (raise to wake)** | SET 0x03 0x28 with 2-byte payload (on_off, show_second). | **9-byte** packet: `03 28 AA/55 05 01 00 00 17 3B` (on/off + extra fields). See `logcat_dumps/set_hand_gesture_wake_on.txt`, `set_hand_gesture_wake_off.txt`. |
| **Auto sport detect** | Not in angelfit table. | **SET 0x03 0x49**: off = `03 49 00 00 00 00 00 00 00 00 00` (11 bytes), on (walk & run) = `03 49 01 01 00 00 00 00 00 00 00`. See `logcat_dumps/set_auto_sport_detect_off.txt`, `set_auto_sport_detect_on_walk_and_run.txt`. |
| **Reminders (drink, walk, stress, woman)** | Partially in capture-backed table (0x47, 0x60, 0x41, 0x42, 0x45). | **Confirmed from dumps**: 0x60 (drinking), 0x47 (walk-around), 0x45 (stress/continuous health), 0x41+0x42 (woman health). VeryFit often sends **v3 cmd 0x09** (HR mode sync) immediately after these SETs. Woman-health order in dump: **0x42** then **0x41**. See `logcat_dumps/set_drinking_cont_*.txt`, `set_walkaround_cont_*.txt`, `set_stress_cont_*.txt`, `set_woman_health_remind_*.txt`. |
| **Music / weather** | SET 0x2A (music), SET 0x2D (weather switch). | Same keys; payloads match dumps: music on `03 2A AA 55`, off `03 2A 55 55` (4 bytes); weather on `03 2D AA 00 00 00`, off `03 2D 55 00 00 00`. See `logcat_dumps/set_music_*.txt`, `set_push_weather_*.txt`. |
| **Watch face** | Bulk write 0x0AF1; control on 0x0AF6 (exact command unknown). | **v3 protocol**: cmd **0x06** = list/select dial (`33 DA AD DA AD 01 0B 00 06 ...`), cmd **0x07**/**0x08** = write dial/JSON; then GET 0xF0 and **D1 01/02/05** chunked transfer for .iwf. See `logcat_dumps/ui_select_watch_face.txt`, `ui_watch_face_write_json.txt`. |
| **Activity** | Legacy activity request (varies by firmware). | **v3 only**: activity = v3 cmd/key **0x001a / 0x0042**; no legacy activity path in capture. |
| **HR state readback** | GET 0x02 0x08 (4× burst in capture when HR toggles). | Same GET 0x08; **v3 cmd 0x09** is used to **get/set** HR continuous state (multi-packet; nseq in payload). |

**Summary:** A200 firmware is **backward compatible** on the wire (same GATT, same GET 0x01/0x02, SET 0x29/0x2A/0x2D, etc.) but adds **v3 (0x33)** for activity, alarms, HR mode sync, and watch face operations, and **new or extended SET keys** (0x32, 0x45, 0x47, 0x49, 0x60, 0x41/0x42) plus **GET 0xA7, 0xB1 (GET_WEATHER_SWITCH), 0x30 (VBUS_EVT_APP_GET_DO_NOT_DISTURB)**. VeryFit uses the extended SET 0x30 and 0x45 (not legacy 0x25) for call alert and continuous HR/Stress on this device. All confirmed commands from the A200 dumps are implemented in the idowatch **Confirmed features (logcat dumps)** section in `htmlapp/index.html`; see `logcat_dumps/*.txt` for exact TX/RX.

**Protocol categories (for reference and `htmlapp/confirmed-only.html`):** Commands are grouped as **GET** (cmd 0x02), **SET** (cmd 0x03), **BIND** (cmd 0x04), **MSG** (cmd 0x05), **Control** (cmd 0x06), **V3** (0x33 …), and **Activity** (02 01 + v3 flow). **MSG 0x05** is how the **phone commands the watch** for notifications: **0x05 0x01** = call notification (KEY_MSG_CALL), **0x05 0x02** = call status (KEY_MSG_CALL_STATUS), **0x05 0x03** = MSG notification (KEY_MSG_MSG). Angelfit/protocol.h: `PROTOCOL_CMD_MSG=0x05`. index.html implements Mi Band style (05 01 + UTF-8), Firmware call (05 01 chunked), and Firmware MSG (05 03 chunked). **Weather** is SET 0x2D (VBUS_EVT_APP_SET_WEATHER_SWITCH). The **confirmed-only** page (`htmlapp/confirmed-only.html`) lists only logcat-confirmed TX, ordered by category and by hex key ascending (e.g. GET 02 01 … 02 F0; SET 0x01 … 0x60; BIND 04 01; then V3 by sub-cmd). It includes **GET 02 05** (Battery, VBUS_EVT_APP_GET_BATT_INFO evt 321), **GET 02 F0** (MTU, VBUS_EVT_APP_GET_MTU_INFO evt 317), **SET 03 01** (Set time, VBUS_EVT_APP_SET_TIME evt 104), and **BIND 04 01** (VBUS_EVT_APP_BIND_START evt 200; from app_fresh_launch.txt).

**Fact-check (logcat_dumps):** The table above was verified against the 28 files in `logcat_dumps/`. Exact TX bytes, payload lengths, and GET/SET keys match for: DND (set_dnd_on/off, **GET 0x30 = VBUS_EVT_APP_GET_DO_NOT_DISTURB**), weather (**GET 0xB1 = GET_WEATHER_SWITCH**), brightness (set_auto_brightness_*), hand gesture (set_hand_gesture_wake_*), auto sport (set_auto_sport_detect_*), drinking/walk/stress/woman (set_drinking_cont_*, set_walkaround_cont_*, set_stress_cont_*, set_woman_health_remind_*), music/weather (set_music_*, set_push_weather_*), HR/stress (set_hr_cont_state_*, set_stress_cont_*, get_hr_cont_state), alarm (get_alarm), device/flash (get_device_info, get_flashbin_info), watch face (ui_select_watch_face, ui_watch_face_write_json). SET 0x30 (notice) is from new_setup.json only; no dedicated notice dump in this repo. **Confirmed-only page** (`htmlapp/confirmed-only.html`) adds GET 02 05 (Battery, evt 321), GET 02 F0 (MTU, evt 317), SET 03 01 (Set time, evt 104; set_time.txt), and BIND 04 01 (evt 200; app_fresh_launch.txt), grouped by category (GET, SET, BIND, V3, Activity) with keys in ascending order.

### New logcat dumps (set_time, set_conn_param, get_sync_health_v3, app_fresh_launch)

Four additional dumps document more of the VeryFit connect/sync flow:

| Dump | Event | TX (exact from logcat) | RX / notes |
|------|--------|------------------------|------------|
| **set_time.txt** | VBUS_EVT_APP_SET_TIME (104) | `03 01 EA 07 03 08 01 11 18 06 00 00 00 00 00 00` (16 B) | No RX in dump. Likely: `03 01` + [year_lo year_hi] [month] [day] [hour] [min] [sec] [weekday?] + padding (e.g. 0x07EA=2026, 03 08=Mar 8, 01 11 18=01:11:18, 06=Saturday). |
| **set_conn_param.txt** | VBUS_EVT_APP_SET_CONN_PARAM (157) | `03 35 02 00 00 00 00 00 00 00 00 00` (12 B) | RX: `03 35 01 00...`. SET 0x35 byte2=02 = conn-param step; reply byte2=01. |
| **get_sync_health_v3.txt** | User info → conn param → v3 health sync | (1) `03 10 B4 40 1F 00 D6 07 03 01` (10 B). (2) `03 35 01...`, `03 35 02...`, then `03 11 01 01 01 00 02 01 00 00 00 01 01 01 01 00 00` (17 B). (3) v3 cmd **0x05** (get sizes): `33 DA AD DA AD 01 88 00 05 00 55 00 01 00 00 00 00 02 01 00 00 00 08 06 00 00 00 03 00 00 00 ...` (136 B + `33 62 EB`). | RX 0x05: `33 DA AD DA AD 01 10 00 05 00 55 00 2F 01 00 00 00 36 9A` — sync all size=303, all_package=3. Sync types: 0x01 SPO2, 0x02 PRESSURE, 0x04 ACTIVITY, 0x06 SWIM, 0x07 SLEEP, 0x08 SPORT, 0x03 HR. Next: v3 cmd **0x04** (SpO2 start, offset 0). |
| **app_fresh_launch.txt** | Full connect + bind + config | 02 01 → 02 02 → 02 07 → 02 F0 → v3 0x1A → 04 01 (bind) → 03 2D → 03 43 (goals) → 03 11 → 02 01 → v3 0x09 → 02 05 → v3 0x07 → 03 10 → 03 11 → 03 E3 10 02 → 03 35 01/02 → 02 A7 → 02 04 (MAC) → 03 01 (set time) → 06 01 → 03 03 … | **02 02** = GET func table (VBUS_EVT_APP_GET_FUNC_TABLE), **02 07** = GET func table ex (VBUS_EVT_APP_GET_FUNC_TABLE_EX), **02 F0** = GET MTU info (VBUS_EVT_APP_GET_MTU_INFO). GET **02 04** = MAC (RX 02 04 F9 24 12 2E 0C 32...). **03 E3**: TX `03 E3 10 02`, RX `03 E3 01 00`. |

**Summary:** SET **0x01** = set time (16 B). SET **0x10** = user info (10 B). SET **0x11** = 17 B config. SET **0x35** = two-step (01/02) for conn param. v3 **cmd 0x05** = get health sync sizes; **cmd 0x04** = start sync per data type (1=SpO2, 2=pressure, 3=HR, 4=activity, 6=swim, 7=sleep, 8=sport). GET **0x04** = MAC. **04 01** = bind start. **03 E3** = unknown (TX 10 02, RX 01 00).

### Activity: v3 health sync vs v3 activity (0x1a/0x42)

**`logcat_dumps/get_sync_health_v3.txt`** is the flow that actually provides health/activity data on watches that use the v3 health sync pipeline. In that dump:

- VeryFit starts a **MANUAL SYNC** (VBUS_EVT_FUNC_START_SYNC_V3_HEALTH).
- It sends **v3 cmd 0x05** (get health sync sizes); the watch replies with sync all size, all_package, etc.
- Then it sends **v3 cmd 0x04** (health data sync) **per data type**: 0x01 SPO2, 0x02 PRESSURE, **0x04 ACTIVITY**, 0x06 SWIM, 0x07 SLEEP, 0x08 SPORT, 0x03 HR. So **activity is requested as v3 health sync type 0x04** (PROTOCOL_V3_HEALTH_DATA_TYPE_ACTIVITY), not as the standalone v3 activity request.

On some watches (e.g. TOOBUR A200 / same firmware as in the dumps), the **standalone v3 activity** (cmd **0x1a** key **0x42**, sent after GET device info in app_fresh_launch) may be **deprecated or return only a legacy/short reply** (e.g. 113-byte single packet, version 0, all zeros). The **real** steps, sport, sleep, etc. are then provided by the **v3 health sync** flow: **cmd 0x05** (get sizes) followed by **cmd 0x04** with the appropriate **data_type** (4 = activity, 7 = sleep, 8 = sport, etc.). See the “Unified v3 health sync” table later in this doc for example TX bytes for cmd 0x04 per type.

**Practical takeaway:** If “Get Activity (02 01 + v3)” returns empty or version‑0 activity, try **Start sync V3 health** (cmd 0x05) then **Sync activity (v3 health type 4)** (cmd 0x04, data_type 4). Replies are v3 multi‑packet; reassembly is the same as for other v3 (33 00 continuation). Parsing the health-sync reply format (head_size, item_count, payload) is device-specific and can be added once you capture a full reply.

### Sending a notification to the watch

**Is it practical?** Yes. The app already writes to **0x0AF6** for Get Info and Get Activity; sending a notification is just writing a different command to the same characteristic (or possibly **0x0AF1** for bulk data). So it's the same mechanism.

**Exact command?** Not documented in public sources. From web search:

- IDO SDK docs describe *enabling* which app notifications are forwarded (e.g. Set smart reminder, Set v3 smart reminder) but not the raw packet that carries the notification *content* (e.g. "Hello" or caller name).
- TOOBUR "Command Center" says: when the phone gets a text, the app sends "a specific hex code" to the watch; 0x0AF6 is for control commands, 0x0AF1 for bulk/data (e.g. watch faces).
- Some other fitness bands (e.g. Mi Band) use a simple format: header bytes (e.g. `0x05 0x01`) followed by UTF-8 message. IDO protocol is different and the exact bytes are unknown.

**Firmware protocol (protocol.h / protocol_send_notice.c):** Realtek/IDO firmware source defines the exact format.

- **Commands:** `PROTOCOL_CMD_GET=0x02`, `PROTOCOL_CMD_SET=0x03`, `PROTOCOL_CMD_MSG=0x05`. Get device info = **0x02 0x01** (PROTOCOL_KEY_GET_DEVICE_INFO). Legacy angelfit firmware defines Set notification switch as **0x03 0x30** with payload `notify_switch`, `notify_itme1`, `notify_itme2`, `call_switch`, `call_delay` (5 bytes). However, **`new_setup.json` shows VeryFit writing a longer 20-byte packet beginning `03 30 88 00 00 aa` and receiving `03 30 88 01 00` back**, so do not assume the short `03 30 01 00 00 01 03` web-app payload is what VeryFit used on this watch.
- **Call notification:** CMD_MSG 0x05 + KEY_MSG_CALL 0x01. Packets are **chunked in 16-byte payloads**. Each BLE write: **[0x05, 0x01, total, serial]** (4 bytes) + **16 bytes payload**. First payload for call: **[phone_number_length, contact_length]** then phone number bytes, then contact (caller name) bytes, zero-padded to 16 bytes. If content fits in one block: total=1, serial=1; payload = 0, contact_len, contact…, pad to 16.
- **Call status:** **0x05 0x02** (PROTOCOL_KEY_MSG_CALL_STATUS) + 1-byte status. **Angelfit** uses **status 0x01** for “stop/end call” (VBUS_EVT_APP_SET_NOTICE_STOP_CALL). protocol_msg_call_status has `uint8_t status`.
- **MSG notification:** Same chunking; cmd/key = **0x05 0x03** (KEY_MSG_MSG). First payload: **type, data_length, phone_number_length, contact_length**, then phone, contact, data text.
- **KEY_MSG_MSG source app (type byte):** The **first byte** of the first 16-byte payload is the **type** (message subtype / source app). **0 = nothing** (invalid; no notification sent). **1 = SMS**, **2 = Mail**, **3 = WeChat**, **4 = Snapchat**, **5 = invalid**, **6 = Facebook**, **7 = Twitter**, **8 = WhatsApp**, **9 = Facebook Messenger**, **10 = Instagram**, **11 = LinkedIn**, **12 = Calendar**, **13 = Skype**. The watch may show an icon or label per type. Set this byte when building the MSG payload so the watch displays the correct app.

**Confirmed:** **Mi Band style (0x05 0x01 + UTF-8)** triggers the **call notification** on many IDO watches. It can stop working if another command (e.g. set-notice **0x03 0x30** or other writes) resets the watch’s call-alert state. **Re-pairing with the VeryFit app** restores call alert and makes 0x05 0x01 work again. So: pair with VeryFit once to enable call notifications; then use the web app with Mi Band format without sending “Enable call alert first” (0x03 0x30), which can reset that state on some devices.

**Reproducibility (why it may work only sometimes):** If the watch’s call-alert state is **reset** by another command (e.g. our “Enable call alert first” **0x03 0x30**, or other set/get commands), **Mi Band style (0x05 0x01 + UTF-8)** may stop triggering the call UI. **Re-pairing with the VeryFit app** restores the state and call notifications work again. So: use VeryFit to enable call alert once; then prefer Mi Band format in the web app and leave “Enable call alert first” unchecked to avoid resetting state. The **firmware chunked format** (0x05 0x01 + total + serial + 16-byte payload) remains an option for devices that expect it.

**What we added:** **Mi Band** (0x05 0x01 + UTF-8) default; **Firmware call** (0x05 0x01 + total + serial + 16-byte payload(s)) with **multi-packet** when caller name > 14 bytes (150 ms delay between chunks); **Firmware MSG** (0x05 0x03 + total + serial + 16B payload(s)) with payload [type, data_length, phone_len, contact_len, sender, message]; **Call status** button: **0x05 0x02** + status byte (0=end/dismiss, 1/2 unknown). Optional **Sender** field for call name / SMS sender; **Enable call alert first** (0x03 0x30) off by default to avoid resetting state.

**If you need SMS or multi-packet call:** The app implements **Firmware MSG** (0x05 0x03, chunked) and **multi-packet Firmware call** (0x05 0x01 when contact > 14 bytes). Use “Sender” for call name / SMS sender; message body in the main text field. Call status **0x05 0x02** + status can dismiss the call UI (status 0 = end).

**Call alert enable/disable (SET 0x30) – research and when it doesn't work**

- **Legacy angelfit:** SET 0x03 0x30 with **5-byte** payload: `notify_switch`, `notify_itme1`, `notify_itme2`, `call_switch`, `call_delay`. Enable: `03 30 01 00 00 01 03` (call on, delay 3 s). Disable: `03 30 00 00 00 00 00`. **GET 0x02 0x10** (PROTOCOL_KEY_GET_NOTICE_STATUS) returns current state: reply bytes are `notify_switch`, `status_code`, `err_code`; use "Get notice status (legacy)" in the app to see what the watch reports.
- **VeryFit / A200:** **Enable** — full 20-byte TX in **app_fresh_launch.txt** line 880: `03 30 88 00 00 AA 00 00 00 00 00 00 00 00 00 00 00 00 00 00`; reply line 882: `03 30 88 01 00` + zeros. **Disable** — no captured app→watch disable. Use **`03 30 88 00 00 55`** + 14 zero bytes: 0x55 = off (same as Music/DND/SOS); the watch reports off as **RX** `03 30 55 01 00...` (app_fresh_launch.txt line 36). Alternative `03 30 88 00 00 00` + padding (0xAA→0x00) is also offered in the app; try 0x55 first. Do not use 0x88 in the 5th byte for off.
- **IDO SDK (GitBook):** [Set smart reminder](https://idoosmart.github.io/IDOGitBook/en/set/IDOSetNoticeFunction.html) describes a high-level model (`IDOSetNoticeInfoBuletoothModel`: `isOnCall`, `callDelay`, `isPairing`, many app toggles) but **does not document raw SET 0x30 bytes**. So 20-byte layout (e.g. meaning of 0x88, 0xAA, 0x55) is inferred from capture and from other SET keys (0x2A, 0x29, 0x2C use 0xAA=on, 0x55=off).
- **If enable/disable still do nothing:** (1) Use **Get notice status (legacy)** before and after to see if the watch changes state (some A200 firmware may ignore legacy GET 0x10 or use GET 0x30 for other readback). (2) **Preferred workaround:** pair with VeryFit once to enable call notifications on the watch, then use the web app only for **sending** notifications (Mi Band style); **do not** send "Enable call alert" or any SET 0x30 from the web app, as that can reset the watch's call state on some devices. (3) To capture a real VeryFit "call alert off": in VeryFit turn off incoming-call notifications while capturing BLE (e.g. nRF Connect or Android HCI snoop) and look for a write to 0x0AF6 with payload starting `03 30`.
- **Device-specific:** On some devices, sending **0x55 in the first payload byte** (angelfit `notify_switch` = off) triggers a **pairing request** on the watch. On that firmware the first byte may not control notifications; use the 5-byte form in confirmed-only.html to test. To avoid pairing when toggling call alert, keep the first byte **0x88** and only change the 5th byte (call_switch).

### V3 protocol – GitHub and official docs (juicy insight)

Web search and official IDO docs surface the following; use them to cross-check our logcat dumps and TOOBUR A200 behaviour.

**Reverse engineering and v3 wire format**

- **xssfox/idowatch** — https://github.com/xssfox/idowatch  
  Reverse-engineering repo (Python + HTML app) for IDO/VeryFit. Same protocol as idowatch; documents 0x0AF0/0x0AF6/0x0AF7 and v3.
- **Bad Smart Watch Auth** — https://sprocketfox.io/xssfox/2025/02/09/ido/  
  Describes v3 in plain terms: first byte **0x33** ("3"); preamble **DA AD DA AD** to detect **new command** vs continuation when BLE splits data; then "service selectorish thing, length, command, sequence fields, data, CRC". Activity request example uses length 0x10, cmd 0x04, sequence 0x0B 0x01, start/stop 0x00, cmd 0x04. **Checksum:** "some sort of CRC16" (device didn't check it in that test). Return data: same header; use sequence numbers to match requests; read until length matches or next preamble. Live demo: https://sprocketfox.io/ido/ (TCX export). Same protocol used by Ryze, Cove, bfit Move, etc.

**Official IDO SMART BAND SDK (GitBook)**

- **Preface / Bluetooth:** https://idoosmart.github.io/IDOGitBook/en/
- **Get v3 HR mode** — https://idoosmart.github.io/IDOGitBook/en/get/IDOGetV3HrFunction.html  
  `getV3HrModeInfoCommand`; model includes **modeType** (0=disable, 1=manual, 2=auto 5min, 3=continuous 5s, 4=default/first sync, 5=custom interval, 6=intelligent 206), time range, **measurementInterval**, **notifyFlag**, high/low HR alert, **hrModeTypes** (5s, 60s, 180s, 300s, 600s, 1800s, smart 255s, 900s). Func table: `funcTable22Model.v3HrData`.
- **V3 heart rate data query** — https://idoosmart.github.io/IDOGitBook/en/query/IDOQueryHrFunction_v3.html  
  Query by year/month/week/day; `IDOSyncSecHrDataInfoBluetoothModel` has itemsCount, secondOffset, silentHeartRate, burnFat/aerobic/limit thresholds and minutes, userMaxHr/userAvgHr, warmUp/anaerobic, heartRates array, highLowHrItems. Matches our v3 cmd 0x09 HR state and GET 0x08 readback.
- **Set v3 HR mode** — Set command list references **Set v3 heart rate mode** (IDOSetV3HrModeFunction).
- **Set alarm** — https://idoosmart.github.io/IDOGitBook/en/set/IDOSetAlarmFunction.html  
  **V2 alarm:** setAllAlarmsCommand. **V3 alarm:** `setV3AllAlarmsCommand` with `IDOSetExtensionAlarmInfoBluetoothModel` (alarmVersion, alarmCount, items). V3-only fields: **repeatTime**, **shockOnOff**, **delayMinute**, **alarmName** (≤23 bytes). Alarm types 0–14 + 42 (custom name).
- **Set watch face ID** — https://idoosmart.github.io/IDOGitBook/en/set/IDOSetWatchDiaFunction.html  
  `setWatchDiaCommand` with **dialId**; func table `funcTable18Model.watchDial`. Matches our v3 cmd 0x06 (list/select) and 0x07/0x08 (write dial/JSON).
- **Set command overview** — https://idoosmart.github.io/IDOGitBook/en/IDOSetUpFunction.html  
  Lists many set commands; v3-related include: Set screen brightness, Set music switch, Set watch face id, Set reminders to move (walk), **Set v3 heart rate mode**, Set pressure switch, **Set menstrual cycle reminders**, **Set menstrual cycle**, **Set drink water reminder**, **Set motion switch** (activity), Set v3 smart reminder, etc. Aligns with our SET 0x32, 0x2A, 0x47, 0x45, 0x41/0x42, 0x60, 0x49 and v3 cmd 0x09.

**Official SDK repos**

- **idoosmart/Flutter_Demo** — https://github.com/idoosmart/Flutter_Demo  
  Flutter SDK demo; Dart + Swift/Java/Kotlin/Obj-C/C. Flutter GitBook: https://idoosmart.github.io/Flutter_GitBook/
- **idoosmart/IDOBlueDemo** — https://github.com/idoosmart/IDOBlueDemo  
  IDO Bluetooth demo (good for seeing which APIs map to v3 vs legacy).

**Takeaways for our dumps**

- v3 **preamble** `33 DA AD DA AD` and **length/cmd/sequence** are confirmed; our activity (0x001a/0x0042), alarm (0x0F), HR mode (0x09), watch face (0x06/0x07/0x08) align with SDK "v3" alarm, v3 HR, and watch dial.
- **V3 HR mode** in SDK (get/set/query) matches our **v3 cmd 0x09** and GET 0x08 burst; modeType 0–6 and intervals (5s, 60s, …) give a semantic map for payloads.
- **V3 alarm** has extra fields (repeatTime, shockOnOff, delayMinute, alarmName); our get_alarm v3 dump is the GET side (cmd 0x0F). **SET alarms** use **v3 cmd 0x0E** (VBUS_EVT_FUNC_V3_SPORT_SORT): one packet with alarm count **0x0A (10)** and per-alarm blocks; bytes **04 19** in the payload are **hour, minute** (4:19 AM). See `logcat_dumps/set_alarms_and_sports.txt`.
- **Watch face:** set dial by ID (SDK) vs our v3 cmd 0x06 (list) + 0x07/0x08 (write JSON/dial data) — SDK is high-level; our dumps show the actual v3 dial list/write packets.

**Do the resources align with our logcat_dumps?**

| Topic | External resource | Our logcat_dumps | Verdict |
|-------|-------------------|------------------|--------|
| **v3 preamble, header & continuation** | xssfox: first byte 0x33, preamble DA AD DA AD; IDO GitBook implies v3 for HR/alarm/dial. | All v3 TX in dumps start with `33 DA AD DA AD` and share a common **12‑byte v3 header**: `33 DA AD DA AD [ver][len_lo][len_hi][cmd_lo][cmd_hi][seq_lo][seq_hi]`. `len` is the total **payload bytes after seq** (not including CRC). When a single v3 command is larger than the negotiated MTU, **continuation packets** are sent as `33 00 00 00 00 00 00 00 00 00 00 00` (0x33 + 11×0x00 “blank header”) followed by more payload bytes. The device reassembles payload bytes from the first headered packet plus all continuations until the final **CRC‑16** is seen; only the **last** continuation ends with CRC. See `set_alarms_and_sports.txt` (v3 cmd 0x0E, alarms) and `get_sync_health_v3.txt` (v3 health sync). The HTML app’s `sendV3PacketChunked` mirrors this: it sends the first 12‑byte header + payload, then streams the remaining payload and CRC behind `33 00…` continuation headers. | **Align.** |
| **GATT** | xssfox + angelfit: 0x0AF0 service, write 0x0AF6, notify 0x0AF7. | VeryFit uses same; dumps show TX to 0x0AF6, RX on 0x0AF7. | **Align.** |
| **Activity v3** | xssfox: activity request uses length 0x10, **cmd 0x04**, sequence 0x0B 0x01, start/stop 0x00, cmd 0x04. | new_setup.json + idowatch: activity = v3 **cmd/key 0x001a / 0x0042** (different cmd/key). | **Differ.** Likely different device/firmware or xssfox’s 0x04 is an inner/version byte; our dumps are authoritative for A200. |
| **v3 HR (get/set)** | IDO GitBook: getV3HrModeInfoCommand, modeType 0–6, measurementInterval, hrModeTypes (5s, 60s, …). | set_hr_cont_state_on/off + get_hr_cont_state: **v3 cmd 0x09** (nseq in payload); GET 0x02 0x08 4× after SET 0x45. | **Align.** SDK semantics match our v3 0x09 and GET 0x08 usage. |
| **v3 alarm** | IDO GitBook: setV3AllAlarmsCommand; v3-only repeatTime, shockOnOff, delayMinute, alarmName. | get_alarm.txt: **v3 cmd 0x0F** (get). **set_alarms_and_sports.txt**: **v3 cmd 0x0E** (set) — single 355 B packet, **10 alarms** (0x0A), per-alarm bytes include **hour, minute** (e.g. `04 19` = 4:19). SDK doesn’t document “get alarm” wire format. | **Align.** We add wire detail (cmd 0x0F get, cmd 0x0E set; 10 slots; time bytes in payload). |
| **Watch face** | IDO GitBook: setWatchDiaCommand(dialId). | ui_select_watch_face: v3 **cmd 0x06**; ui_watch_face_write_json: v3 **cmd 0x07** then 0x08, then GET 0xF0, **D1 01/02/05** chunked. | **Align.** Dumps show the actual v3 dial list (0x06) and write (0x07/0x08) + transfer; SDK is high-level. |
| **SET keys** | IDO Set overview: screen brightness, music, watch face, walk remind, v3 HR, pressure, menstrual, drink water, motion switch. | Dumps: **0x32** (brightness), **0x2A** (music), **0x47** (walk), **0x45** (stress/HR), **0x41/0x42** (woman), **0x60** (drink), **0x49** (auto sport). | **Align.** Same feature set; dumps give exact payloads. |
| **Hand gesture** | Angelfit: SET 0x28 with 2-byte payload (on_off, show_second). | set_hand_gesture_wake_on/off: **9-byte** payload `03 28 AA/55 05 01 00 00 17 3B`. | **Differ.** A200 uses extended 9-byte format; angelfit is legacy 2-byte. (Already in A200 vs angelfit table.) |
| **CRC** | xssfox: “some sort of CRC16”; device didn’t check. | Standard **CRC-16-CCITT/FALSE** (poly 0x1021, init 0xFFFF). Computed over bytes **1 to length-3** of the logical v3 frame (i.e. from the first **0xDA** in the preamble through the last payload byte, excluding the leading `0x33` and the two trailing CRC bytes). Even when a frame is split into multiple BLE packets, **CRC is calculated once over the full reassembled frame and appears only at the very end** of the last continuation packet. | **Align.** (We added precise definition and continuation semantics). |
| **GET 0xA7, 0xB1, 0x30** | Not in angelfit or xssfox. | get_flashbin_info: **GET 0xA7**; **GET 0xB1** = **GET_WEATHER_SWITCH** (evt 316); **GET 0x30** = **VBUS_EVT_APP_GET_DO_NOT_DISTURB** (DND read, evt 326). | **Dumps add.** SDK doesn’t document these GET keys; dumps confirm A200/VeryFit use. |

**Summary:** Resources and dumps **align** on v3 preamble, GATT, v3 HR (0x09 + GET 0x08), v3 alarm get (0x0F), watch face (0x06/0x07/0x08), and SET key list. They **differ** on (1) **activity v3 cmd** (xssfox 0x04 vs our 0x001a/0x0042) — treat our dumps as correct for A200; (2) **hand gesture** payload length (angelfit 2-byte vs A200 9-byte). The dumps **add** wire-level detail for GET 0xA7, **0xB1 (GET_WEATHER_SWITCH)**, **0x30 (VBUS_EVT_APP_GET_DO_NOT_DISTURB)** and exact v3 packet bytes the SDK does not publish.

### VBUS event categories and hex codes

VeryFit logcat uses **VBUS event** names and numeric **evt** IDs. The **parent category** is logged as `evt base:`; the **child event** is the specific operation. Wire hex (TX to 0x0AF6) is determined by the evt; the tables below map categories and selected events to hex from `logcat_dumps/*.txt`.

**1. VBUS_EVT_BASE (parent category)**

- **VBUS_EVT_BASE_APP_GET** — Base for all **GET** (read) requests. Log line: `api sysEvtSet,intput evt base:VBUS_EVT_BASE_APP_GET evt:…`. The **evt** value is the specific GET (e.g. 301, 302, 326); the wire is **cmd 0x02** + key byte(s).
- **VBUS_EVT_BASE_APP_SET** — Base for all **SET** (write) requests. Log: `evt base:VBUS_EVT_BASE_APP_SET evt:…`. Wire is **cmd 0x03** (or 0x04 for BIND, etc.) + key + payload.

| Evt (decimal) | VBUS name / meaning | Wire (hex) | Source |
|---------------|---------------------|------------|--------|
| 301 | VBUS_EVT_APP_GET_DEVICE_INFO | **02 01** | app_fresh_launch.txt |
| 302 | VBUS_EVT_APP_GET_FUNC_TABLE | **02 02** | app_fresh_launch.txt |
| 311 | VBUS_EVT_APP_GET_FUNC_TABLE_EX | **02 07** | app_fresh_launch.txt |
| 317 | VBUS_EVT_APP_GET_MTU_INFO | **02 F0** | app_fresh_launch.txt |
| 321 | VBUS_EVT_APP_GET_BATT_INFO | **02 05** | app_fresh_launch.txt |
| 322 | VBUS_EVT_APP_GET_FLASH_BIN_INFO | **02 A7** | get_flashbin_info.txt, app_fresh_launch.txt |
| 326 | VBUS_EVT_APP_GET_DO_NOT_DISTURB | **02 30** | app_fresh_launch.txt, set_dnd_*.txt |
| 300 | VBUS_EVT_APP_APP_GET_MAC | **02 04** | app_fresh_launch.txt |
| 316 | GET_WEATHER_SWITCH | **02 B1** | set_dnd_*.txt, app_fresh_launch.txt (weather flow); set_push_weather_*.txt |
| 422 | (base VBUS_EVT_BASE_APP_GET) HR/health state readback | **02 08** | ui_watch_face_write_json.txt (evt:422, cmd 0x2 0x8) |

**2. VBUS_EVT_FUNC (parent category — 5xxx events)**

- **VBUS_EVT_FUNC_*** — “Func” events are **v3 (0x33)** operations. Log: `app send protocol evt:5xxx(VBUS_EVT_FUNC_…)`. Wire is **v3 packet**: `33 DA AD DA AD …` with **cmd** in bytes 8–9 (e.g. 0x0E, 0x0F, 0x09).

| Evt (decimal) | VBUS name | Wire (v3) | Source |
|---------------|-----------|-----------|--------|
| 5010 | VBUS_EVT_FUNC_V3_SET_HR_MODE (search also **hr_mode_set**, **func_v3_set_hr_mode** in native SDK) | v3 **cmd 0x09** (17 09 / 14 09 in payload) | set_hr_cont_state_*.txt, set_drinking_cont_*.txt; **wire notes:** [docs/v3_set_hr_mode_continuous.md](docs/v3_set_hr_mode_continuous.md) |
| 5013 / 5017 | VBUS_EVT_FUNC_V3_SPORT_SORT | v3 **cmd 0x0E** (set alarms + sport order; 355 B) | set_alarms_and_sports.txt (evt 5017), app_fresh_launch.txt (5013) |
| 5018 | VBUS_EVT_FUNC_V3_GET_ALARM | v3 **cmd 0x0F** — TX e.g. `33 DA AD DA AD 01 0C 00 0F 00 24 01 00 28 18` | get_alarm.txt |

**3. VBUS_EVT_APP (weather and other APP events)**

**Naming: SET vs GET vs other** — **VBUS_EVT_APP_SET_*** = app writes config to the device → wire cmd **0x03** (SET) + key + payload. **VBUS_EVT_APP_GET_*** = app reads from the device → wire cmd **0x02** (GET) + key. So SET = host write, GET = host read. Events without SET/GET in the name use other wire commands (e.g. WEATCHER_DATA → 0A 01, BIND_START → 04 01). **VBUS_EVT_APP_APP_*** (double APP) is a sub-category (e.g. APP_GET_MAC, APP_TO_BLE_MUSIC_*); wire is still 0x02 or 0x03. **VBUS_EVT_BASE_APP_SET** / **VBUS_EVT_BASE_APP_GET** are the SDK event base classes; for wire protocol we ignore BASE_APP and use SET=0x03, GET=0x02, etc.

- **VBUS_EVT_APP_SET_WEATHER_SWITCH** (logcat sometimes shows "WEATHER" or "WEATCHER" in variants; same event) — Weather push on/off. Evt **150**. Wire: **SET 0x03 0x2D** + payload (e.g. `03 2D 55 00 00 00` = off, `03 2D AA 00 00 00` = on).

| Evt | VBUS name | Wire (hex) | Source |
|-----|-----------|------------|--------|
| 150 | VBUS_EVT_APP_SET_WEATHER_SWITCH | **03 2D** [55\|AA] 00 00 00 | app_fresh_launch.txt, set_push_weather_*.txt |
| 116 | VBUS_EVT_APP_SET_DO_NOT_DISTURB | **03 29** + 14-byte payload | set_dnd_on.txt |
| 117 | VBUS_EVT_APP_SET_MUISC_ONOFF | **03 2A** AA/55 55 | set_music_*.txt |
| 104 | VBUS_EVT_APP_SET_TIME | **03 01** + 16-byte time | set_time.txt |
| 200 | VBUS_EVT_APP_BIND_START | **04 01** F1 01 01 02 02 01 00 | app_fresh_launch.txt |

**VBUS_EVT_APP_APP_TO_BLE_MUSIC_*** — **Start** (evt 500) and **Stop** (evt 501) are **Control cmd 0x06 0x01**, not SET 0x2A. Wire: **06 01 00 00 00 00** = music start (play), **06 01 01 00 00 00** = music stop (pause). VeryFit sends 0x06 0x01 after SET 0x2A (music on/off). set_music_on.txt, set_music_off.txt.

**VBUS_EVT_APP_WEATCHER_* (weather data and city name)** — Logcat uses the spelling **WEATCHER** (likely SDK typo for “weather”). After enabling the weather switch (evt 150), VeryFit sends weather data and then city name. Wire uses **cmd 0x0A** (WEATHER) with subcmd in second byte:

| Evt | VBUS name | Wire (hex) | Source |
|-----|-----------|------------|--------|
| 153 | VBUS_EVT_APP_WEATCHER_DATA | **0A 01** + payload (weather data: today_type, temps, humidity, uv, aqi, forecast). Example TX: `0A 01 02 08 09 07 5B 00 00 02 0E 08 02 10 09 02 0F 09` (18 B). RX: `0A 01 00 00 00...` (ACK). | set_push_weather_on.txt |
| 6500 | VBUS_EVT_APP_WEATCHER_CITY_NAME | **0A 02** + length (1 B) + UTF-8 city name, null-padded. Example: `0A 02 06 4C 6F 6E 64 6F 6E 00 00 00 00 00 00 00 00 00 00` (20 B) = city "London" (len 6). Sent after WEATCHER_DATA. | set_push_weather_on.txt |

So **0x0A 0x01** = set weather data (struct protocol_weatch_data); **0x0A 0x02** = set weather city name. Both are sent to 0x0AF6 like other commands. See `logcat_dumps/set_push_weather_on.txt` (lines 18–36) for the full sequence: 150 → 153 → 6500 → 153 again → 6500 again (retries until ACK).

**Note:** Evt numbering is firmware/SDK-specific; not every evt has a 1:1 mapping to a single hex key (e.g. 301 → 0x01, 302 → 0x02, but 321 → 0x05, 322 → 0xA7). The wire bytes above are taken from the referenced logcat dumps.

### Inferring hex bytes from SDK “order” (no simple leak)

Checked whether **IDOBlueProtocol** or **IDOAndroidBleSDK** expose command hex bytes via **ordering** (e.g. enum position = key byte).

**IDOFoundationCommand.h (iOS):**

- **get\*Command** declarations are in a fixed order (getMacAddr, getDeviceInfo, getFuncTable, getLiveData, getDeviceTime, … getFlashBinInfo, getBatteryInfo, getMtuInfo, getScreenBrightness, getHandUpGesture, getNotDisturb, …). That order **does not** match GET key bytes: e.g. wire has **02 01** = device, **02 02** = func, **02 04** = MAC, **02 05** = battery, **02 32** = brightness, **02 30** = DND, **02 A7** = flashbin, **02 F0** = MTU. So “first get = 0x01, second = 0x02” does not hold; the header order is API grouping, not protocol key order.
- **set\*Command** declarations (setCurrentTime, setAlarm, setUserInfo, setFindPhone, setHandUp, setOpenMusic, setNoDisturbMode, setScreenBrightness, setConnParam, setMenstrual, setWalkReminder, setDrinkReminder, …) also do **not** line up with SET key bytes (03 01, 03 22, 03 28, 03 29, 03 2A, 03 32, 03 41/42, 03 45, 03 47, 03 60, …). So no “index = key” leak there.

**IDOGetInfoBluetoothModel.h:**

- Contains **“获取第 N 个功能表”** (Get func table N) with **N = 42, 41, … 11** — i.e. **explicit table index**. That maps to the **extended function table** (Part 2), not to GET/SET command keys. We already document that in **ido_func_tables.h** (tables 11–42 and their bits). So the only “order” that matches our repo is **function table index**, which we have; it does not give SET/GET hex keys.

**Logcat “config table index”:**

- VeryFit logcat shows **cur config table index: 0, 1, 2, 8, 9, 11, 15, 16, 18, 19, 20, 23, 24, 30, 31, 32, 33, 35, 36, 38, 39, 49, 50** with events like SET_TIME(104), SET_SCREEN_BRIGHTNESS(154), SET_DO_NOT_DISTURB(116). That index is the **sync order** used by `protocol_sync_config.c` (which config to send next), **not** the wire key: e.g. index **30** = SET_SCREEN_BRIGHTNESS but wire is **03 32**, not 03 1E. So config table index cannot be used to infer SET/GET key bytes.

**Conclusion:** The IDO SDK headers do **not** leak command hex bytes by order. VBUS evt IDs and wire keys come from the **native protocol** (logcat dumps / VeryFit C code), not from the IDO ObjC/Java API order. To get hex bytes we keep using **logcat_dumps** and the tables in this doc.

**Closest SDK order to logcat:** The **set\*Command** block in **IDOFoundationCommand.h** (lines ~577–1102: `setCurrentTimeCommand` through `setDrinkReminderCommand`) is the SDK stretch whose order **most resembles** the logcat sync order from `app_fresh_launch.txt` (config table index 8→50). Matching run: **setCurrentTime** → **setUserInfo** → **setCalorieAndDistanceGoal** (exact); then **setFindPhone** → **setHandUp** → **setOpenMusic** → **setWeather** → **setNoDisturbMode** → **setHrInterval** (contiguous in both; logcat has SET_PRESSURE between FindPhone and HandUp, SDK has setPressureSwitch much later); then **setScreenBrightness** → **setMenstrual** → **setMenstrualRemind** (exact); then **setWalkReminder** → **setActivitySwitch** → **setDrinkReminder** (exact). Differences: **setSwitchNoticeCommand** is early in the SDK (after setTargetInfo) but last in logcat (config index 50); **setPressureSwitchCommand** is late in the SDK but at index 16 in logcat; **setHrModeCommand** is in the SDK block after setWeather but V3_SET_HR_MODE is at index 39 in logcat. So the “sync order” used by VeryFit is closest to the **middle block of set\*Command** in IDOFoundationCommand.h, not to get\*Command order or to IDOGetInfoBluetoothModel interface order.

### IDO docs v3 (official GitBook)

The **IDO SMART BAND SDK** (GitBook) describes v3 at the **API level only** — high-level models and command names, **not** raw wire bytes or the `33 DA AD DA AD` packet layout. Cross-check with our logcat dumps and xssfox reverse engineering for actual v3 wire format.

| Doc topic | URL | What the docs say | Our wire (from dumps) |
|-----------|-----|-------------------|------------------------|
| **Preface / Bluetooth** | https://idoosmart.github.io/IDOGitBook/en/ | IDOBluetooth, IDOBlueProtocol (C), IDOBlueUpdate; scan, connect, bind, sync config, sync health. | Same GATT 0x0AF0/0xAF6/0xAF7/0xAF1; v3 packets on 0xAF6. |
| **Get v3 HR mode** | https://idoosmart.github.io/IDOGitBook/en/get/IDOGetV3HrFunction.html | `getV3HrModeInfoCommand`; **IDOSetV3HeartRateModeBluetoothModel**: modeType (0=disable, 1=manual, 2=auto 5min, 3=continuous 5s, 4=default/first sync, 5=custom interval, 6=intelligent 206), time range, measurementInterval, notifyFlag, high/low HR alert, hrModeTypes (5s, 60s, 180s, 300s, 600s, 1800s, smart 255s, 900s). Func table: `funcTable22Model.v3HrData`. | **v3 cmd 0x09** (get/set HR mode); GET 0x02 0x08 readback after SET 0x45. set_hr_cont_state_*.txt, get_hr_cont_state.txt. |
| **Set v3 HR mode** | (Set command list; Set v3 heart rate mode — link may be .md) | Set v3 heart rate mode listed under Set command overview. | v3 cmd 0x09 (multi-packet; nseq in payload). |
| **V3 heart rate data query** | https://idoosmart.github.io/IDOGitBook/en/query/IDOQueryHrFunction_v3.html | Query by year/month/week/day; **IDOSyncSecHrDataInfoBluetoothModel**: itemsCount, secondOffset, silentHeartRate, burnFat/aerobic/limit thresholds and minutes, userMaxHr/userAvgHr, warmUp/anaerobic, heartRates array, highLowHrItems. | v3 cmd 0x09 + GET 0x08; health sync v3 cmd 0x04 (data type 3 = HR). get_sync_health_v3.txt. |
| **Set alarm** | https://idoosmart.github.io/IDOGitBook/en/set/IDOSetAlarmFunction.html | **V2:** `setAllAlarmsCommand` (IDOSetAlarmInfoBluetoothModel). **V3:** `setV3AllAlarmsCommand` with **IDOSetExtensionAlarmInfoBluetoothModel** (alarmVersion, alarmCount, items). V3-only fields: **repeatTime**, **shockOnOff**, **delayMinute**, **alarmName** (≤23 bytes). Alarm types 0–14 + 42 (custom name). | **GET alarm** = v3 cmd **0x0F**. **SET alarms** = v3 cmd **0x0E** (VBUS_EVT_FUNC_V3_SPORT_SORT, 355 B, 10 alarm slots). set_alarms_and_sports.txt, get_alarm.txt. |
| **Set watch face ID** | https://idoosmart.github.io/IDOGitBook/en/set/IDOSetWatchDiaFunction.html | `setWatchDiaCommand` with dialId; func table `funcTable18Model.watchDial`. | v3 cmd **0x06** (list/select), **0x07**/ **0x08** (write dial/JSON); then GET 0xF0 and D1 01/02/05 chunked .iwf. ui_select_watch_face.txt, ui_watch_face_write_json.txt. |
| **Set command overview** | https://idoosmart.github.io/IDOGitBook/en/IDOSetUpFunction.html | Lists set commands; v3-related: Set screen brightness, Set music switch, Set watch face id, Set reminders to move (walk), **Set v3 heart rate mode**, Set pressure switch, Set menstrual cycle reminders, Set drink water reminder, Set motion switch, **Set v3 smart reminder**, etc. | SET 0x32, 0x2A, 0x47, 0x45, 0x41/0x42, 0x60, 0x49; v3 cmd 0x09 for HR. |

**Summary:** The GitBook does **not** document the v3 **wire format** (preamble `33 DA AD DA AD`, length, cmd, sequence, CRC). It documents **v3 features** (HR mode, v3 alarm, v3 HR query, watch dial) and high-level APIs. For wire-level v3 (cmd 0x04, 0x05, 0x09, 0x0E, 0x0F, 0x06, 0x07, 0x08, activity 0x001a/0x0042), use our logcat dumps and TOOBUR tables; xssfox’s post describes the v3 packet structure.

### References / URLs

**IDO protocol, BLE, and testing (general):**

- https://sprocketfox.io/xssfox/2025/02/09/ido/ — Bad Smart Watch Auth; IDO/VeryFit reverse engineering, 0x0AF0/0x0AF6/0x0AF7, v3 protocol, live demo.

**Angelfit (orangebrush) — local `angelfit/` and https://github.com/orangebrush/angelfit:**

- **UUIDConfigure.swift:** Service **0x0AF0**; **write 0x0AF6** (commands: get info, set notice, call/SMS notification, call status); **read/notify 0x0AF7**; **bigWrite 0x0AF1** (health/sync data); **bigRead 0x0AF2**. Same GATT layout as idowatch.
- **protocol_write.c:** **Call status “stop call”** = VBUS_EVT_APP_SET_NOTICE_STOP_CALL → **0x05 0x02 0x01** (struct protocol_cmd: head + cmd1=0x01). So status **0x01** = end/dismiss call in angelfit.
- **Get notice status:** PROTOCOL_KEY_GET_NOTICE_STATUS = **0x10** → **0x02 0x10** (GET cmd + key). Device replies on 0x0AF7 with current notice/call-alert state.
- **protocol_send_notice.h:** PROTOCOL_SEND_NOTICE_TYPE_CALL = 0xF100, TYPE_MSG = 0xF200; for SMS the low byte of type is the message subtype in the payload.
- Commands (including 0x05 0x01/0x02/0x03) use **write (0x0AF6)** with **.withResponse**; health sync uses **bigWrite (0x0AF1)**.

**Command reference (angelfit protocol — all to 0x0AF6, replies on 0x0AF7):**

| Cmd | Key | Description | Payload (after cmd, key) |
|-----|-----|-------------|---------------------------|
| **GET 0x02** | 0x01 | Device info | (none) |
| | 0x02 | Func table (VBUS_EVT_APP_GET_FUNC_TABLE) | (none) |
| | 0x03 | Device time | (none) → reply: year, month, day, hour, min, sec, week |
| | 0x04 | MAC | (none) → reply: 6 bytes MAC |
| | 0x05 | Battery info (VBUS_EVT_APP_GET_BATT_INFO evt 321) | (none) → reply: type, voltage, status, level |
| | 0x06 | SN info | (none) → reply: device-specific serial/SN |
| | 0x10 | Notice status | (none) → reply: notify_switch, status_code, err_code |
| | 0x07 | Func table extended (VBUS_EVT_APP_GET_FUNC_TABLE_EX) | (none) → reply: 40:24:40:ff:… (see new_setup.json, app_fresh_launch.txt) |
| | 0xF0 | MTU info (VBUS_EVT_APP_GET_MTU_INFO) | (none) → Reply 8 bytes after 02 F0: **00 89 00 89 00 e8 03 8c 00**. Decoded: byte 3 = **tx_mtu = 137** (0x89), byte 5 = **rx_mtu = 137**; bytes 7–8 uint16 LE = **1000** (0x03E8, e.g. max frame/buffer); byte 9 = **140**. So **137** is the negotiated BLE ATT MTU (common after MTU exchange; 137 − 3 = 134 payload). app_fresh_launch.txt. |
| | 0x08 | Continuous HR / health config (evt 422, VBUS_EVT_BASE_APP_GET) | (none) → Logcat shows **evt 422** (base **VBUS_EVT_BASE_APP_GET**) triggers TX `02 08` (ui_watch_face_write_json.txt lines 1204–1208). App sends 02:08 four times after continuous HR toggle in hr_cont_enabled.json / healthdata_toggles.json. Likely readback of HR/health state. Reply format on 0x0AF7 not fully documented. |
| | 0xA0 | Live data | (none) → reply: step, calories, distances, active_time, heart_rate |
| | **0x20** | **HR sensor param** | (none) → reply: rate (uint16), led_select (uint8) — debug/spec |
| | **0x21** | **G-sensor param** | (none) → reply: rate (uint16), range (uint8), threshold (uint16) — debug/spec |
| | **0x30** | **VBUS_EVT_APP_GET_DO_NOT_DISTURB (DND read)** | (none) → Reply **byte 2** = DND state: **0x55** = off, **0xAA** = on. Full reply e.g. `02 30 55 17 00 07 00 02 FE 55 17 00 07 00...` (set_dnd_off.txt line 28). Rest of payload not fully confirmed. Evt 326. See set_dnd_on/off, app_fresh_launch.txt. |
| | **0xA7** | **Flashbin info (A200)** | (none) → reply e.g. `02 A7 00 01 01 78 56 34 12`. See logcat_dumps/get_flashbin_info.txt. |
| | **0xB1** | **GET_WEATHER_SWITCH** | (none) → reply includes weather switch state (e.g. `02 B1 AA/55...`; 0x55=off, 0xAA=on). Evt 316. See logcat_dumps set_push_weather_*.txt, set_dnd_*.txt, app_fresh_launch.txt. |
| **SET 0x03** | 0x01 | Set device time (VBUS_EVT_APP_SET_TIME evt 104) | year(2), month, day, hour, minute, second, week — 16 B e.g. set_time.txt |
| | **0x02** | **Set alarm** | alarm_id, status, type, hour, minute, repeat, tsnooze_duration — see **Alarm support** below; only if func table alarm_num > 0 |
| | **0x04** | **Sleep goal** | hour, minute (target sleep duration) — only if func table main_func sleep(1) |
| | 0x22 | Set hand | hand_type (0=left, 1=right) |
| | 0x26 | Find phone | status, timeout (seconds) |
| | 0x27 | Factory defaults | (none) — restore default config; only if func table configDefault |
| | 0x28 | Up hand gesture | A200/VeryFit: **9-byte** payload `03 28 AA/55 05 01 00 00 17 3B` (on_off, then 7 more bytes). Angelfit legacy: on_off (0xAA=on, 0x55=off), show_second (2–7). |
| | 0x29 | Do not disturb | A200: **14-byte** payload after 03 29 (switch, start/end time blocks). Angelfit legacy: switch_flag, start_hour, start_minute, end_hour, end_minute (5 bytes). Readback: GET 0x02 0x30 (VBUS_EVT_APP_GET_DO_NOT_DISTURB). |
| | 0x2A | Music on/off | switch_status: 0xAA=on, 0x55=off (firmware convention; same as VeryFit) |
| | 0x2C | One-key SOS | on_off (0xAA=on, 0x55=off) |
| | 0x2D | Set weather switch | cmd1, cmd2, cmd3 (e.g. 1,0,0 = on; 0,0,0 = off) — only if func table weather(7) is set |
| | 0x30 | Set notice | Legacy angelfit struct = `notify_switch, notify_itme1, notify_itme2, call_switch, call_delay`. In `new_setup.json`, VeryFit instead writes **20 bytes** starting `88:00:00:aa:00…` and gets `03:30:88:01:00` back, so this key is newer / wider than the simple 5-byte form on this watch/app combination. |
| | 0x35 | Unknown (VeryFit) | Writes seen: `03:35:02:00:00:…` and `03:35:01:00:00:…`; replies seen: `03:35:02:00`, `03:35:01:00`, `03:35:02:0f`. Purpose unknown. |
| | 0x41 | Women's health config? | Capture-backed from `healthdata_toggles.json`: setup/default writes are all-zero after the header, while later writes become dated payloads like `03:41:55:07:1c:ea:07:03:07:0e:05:04:00:55` and `03:41:aa:...`; likely part of menstrual / women's-health reminder state. |
| | 0x42 | Women's health detail? | Capture-backed companion to `0x41`: default `03:42:00:00:00:00:00:00:00`, later `03:42:03:03:08:00:03:03:03`; likely the small rule / cycle block paired with `0x41`. |
| | 0x45 | Continuous health config? | Capture-backed from `healthdata_toggles.json`: the payload flips between `03:45:55:09:00:12:00:55:3f:3c:00:50:00:01:00:1e` and `03:45:aa:...`. This is the only plausible watch-side family for VeryFit's continuous-HR / continuous-stress UI in that trace, but the dump does not separate those two features cleanly. |
| | 0x47 | Walk-around reminder? | Capture-backed from `healthdata_toggles.json`: `03:47:01:64:00:09:00:15:00:fe:00:00:73:00:00:00:01` then the same packet with byte 2 = `00`, both ACKed. Likely sedentary / walk-around reminder. |
| | 0x60 | Drinking reminder? | Capture-backed from `healthdata_toggles.json`: `03:60:01:09:00:12:00:3f:1e:00:01:00:00:00:00:00` then `03:60:00:09:00:12:00:3e:1e:00:01:00:00:00:00:00`, both ACKed. Likely drink-water reminder. |
| | **0x24** | **Heart rate interval (`set_hr_interval` / VBUS_EVT_APP_SET_HEART_RATE_INTERVAL, evt 112)** | **Short form:** `03 24` + 3 BPM thresholds (angelfit). **VeryFit sync:** **20 B** payload — see [docs/set_hr_interval_0324.md](docs/set_hr_interval_0324.md). `app_fresh_launch.txt`: `03 24 78 8C B4 C8 64 78 8C A0 B4 14 00 00 00 00 17 3B C8 00`. |
| | **0x25** | **Heart rate mode** | mode: **0x55=off (close)**, **0x88=auto (continuous)**, **0xAA=manual** — this is the heart rate enable/disable (angelfit CoreDataHandler default 0x88) |
| | **0x52** | **Real-time sensor status** | gsensor_status, heart_rate_sensor_status (2 bytes): **0x55=off, 0xAA=on** per byte. App: Real-time sensors off / HR stream on / both on. |
| **BIND 0x04** | 0x01 | Bind start (VBUS_EVT_APP_BIND_START evt 200) | 9 B: `04 01 F1 01 01 02 02 01 00` (app_fresh_launch.txt). Sent after GET MTU; watch may reply to confirm bind mode. |
| **WEATHER 0x0A** | 0x01 | Set weather data | struct protocol_weatch_data: today_type, today_tmp, today_max_temp, today_min_temp, humidity, uv_intensity, aqi, future[3] (each: type, max_temp, min_temp) — only if func table weather(7) is set |
| **APP_CONTROL 0x06** | 0x01 | Music | cmd1: 0x00=start, 0x01=stop |
| | 0x02 | Photo | cmd1: 0x00=start, 0x01=stop |
| | 0x04 | Find device | cmd1: 0x00=start, 0x01=stop |
| | 0x03 | Single sport | cmd1: 0x00=start, 0x01=stop — only if func table single_sport(2) is set |
| | 0x30 | Open ANCS | (none or zeros) |
| | 0x31 | Close ANCS | (none or zeros) |
| **MSG 0x05** | 0x01 | Call notification | chunked: total, serial, 16B payload(s) |
| | 0x02 | Call status | status (0x01=end call) |
| | 0x03 | SMS notification | chunked: total, serial, 16B payload(s) |
| **RESET 0xF0** | 0x01 | Reboot | (none) — watch reboots; connection drops |

**Note:** **BLE_CONTROL (cmd 0x07)** in the firmware is used for *watch → app* events (e.g. user triggers find-phone or one-key SOS on the watch; keys 0x02, 0x03, 0x04, 0x10, 0x11). The app does not send 0x07 to the watch for those; SET/APP_CONTROL cover the app→watch side.

The idowatch htmlapp implements all of the above; GET replies for time, MAC, battery, live data, legacy notice status, SN info, **HR sensor param (0x20)**, and **G-sensor param (0x21)** are parsed and shown in the event log. Capture-backed raw replies such as **GET 0x02 0x07 (func table ex)**, **GET 0x02 0x30 (VBUS_EVT_APP_GET_DO_NOT_DISTURB, DND read)**, **GET 0x02 0xF0 (MTU info)**, **GET 0xA7**, **GET 0xB1 (GET_WEATHER_SWITCH)**, **`0x03 0x30` notice-status notifications**, and named ACK/status logs for **`0x41 / 0x42 / 0x45 / 0x47 / 0x60`** are also shown. The page no longer treats `03:30:55:01:00` as live HR, and it now includes exact capture-backed buttons for the likely **drink** (`0x60`) and **walk-around** (`0x47`) reminders.

**Commands in protocol but not (yet) in the app:** sport goal (0x03), user info (0x10), unit (0x11), long sit (0x20), lost find (0x21), sys OS (0x23), display mode (0x2B), sport mode select (0x2E), lost find mode (0x40), HR/G-sensor params SET (0x50/0x51), etc. Sending weather data (WEATHER 0x0A 0x01 + payload) has no UI yet—only the weather switch (SET 0x2D) is in the app.

**Observed VeryFit BLE flow (new_setup.json):** GATT discovery maps **0x0AF6** value handle **0x0010**, **0x0AF7** value handle **0x0012** (+ CCCD **0x0013**), **0x0AF2** value handle **0x0015** (+ CCCD **0x0016**), and **0x0AF1** value handle **0x0018**. VeryFit enables notifications on **both `0x0AF7` and `0x0AF2`**, but every application payload in this capture is either a **host write to `0x0AF6`** or a **watch notification on `0x0AF7`**; `0x0AF2` stays silent after its CCCD write.

**Important correction:** `03:30:55:01:00` is **not** a host `SET 0x30` and **not** live HR `85 bpm`. It is a **watch status notification** on `0x0AF7`, likely the legacy `protocol_set_notice_ack` (`notify_switch=0x55`, `status=1`, `err=0`), and it arrives immediately after the first `GET 0x04` write.

**First-session host writes (abbreviated):** `GET 0x04` (MAC) → `GET 0x02` (func table) → `GET 0x07` → `GET 0xF0` → **v3 activity request** (`0x001a/0x0042`) → `GET 0x30` → `GET 0x01` (device info) → `SET 0x10` → v3 `0x0043/0x0044/0x0045` → `GET 0x04` again → `SET 0x11` → `GET 0x04` again → `GET 0xA7` → `GET 0x01` → `SET 0xE3` → `SET 0x01` (time) → v3 `0x0046/0x0047/0x0048` → more config writes (`0x26`, `0x45`, `0x2A`, `0x2D`, `0x24`, `0x41`, `0x42`, `0x43`, `0x60`) → **SET 0x30** (20 B: `03 30 88 00 00 AA` + 14 zeros — **app_fresh_launch.txt** line 880) → `SET 0x35`. So VeryFit does a broader setup sweep than idowatch’s minimal `GET device info → activity` flow, but the trace does **not** show a factory-defaults or reboot command.

**GET 0x02 0x07 / 0x02 0x08 / 0x02 0x30 / 0x02 0xF0 / 0xA7 / 0xB1 (from capture; VBUS names from app_fresh_launch.txt):**
- `GET 0x02 0x08` = **evt 422**, base **VBUS_EVT_BASE_APP_GET** (ui_watch_face_write_json.txt lines 1204–1208: `api sysEvtSet,intput evt base:VBUS_EVT_BASE_APP_GET evt:422` → TX `02 08`). Sent 4× after HR/health toggles (hr_cont_enabled.json, healthdata_toggles.json). Reply format on 0x0AF7 not fully documented.
- `GET 0x02 0x02` = **VBUS_EVT_APP_GET_FUNC_TABLE** (func table). Reply: 15-byte capability bitmap.
- `GET 0x02 0x07` = **VBUS_EVT_APP_GET_FUNC_TABLE_EX** (extended func table). Reply: `02:07:40:24:40:ff:38:4e:d3:ff:0b:08:00:84:95:c7:06:01:00:34` (format unknown).
- `GET 0x02 0x30` = **VBUS_EVT_APP_GET_DO_NOT_DISTURB** (DND read; evt **326**). VeryFit sends TX `02 30` after SET DND and in config-sync; reply byte 2 = DND state (0x55=off, 0xAA=on). Reply in set_dnd_on/off: `02 30 55/AA 17 00 07 00 02 FE 55 17 00 07 00...`. Distinct from legacy GET 0x10 notice status.
- `GET 0x02 0xF0` = **VBUS_EVT_APP_GET_MTU_INFO**. Reply: `02:f0:00:89:00:89:00:e8:03:8c:00`. Decoded: **tx_mtu = 137** (byte 3, 0x89), **rx_mtu = 137** (byte 5); bytes 7–8 uint16 LE = **1000**; byte 9 = **140**. Firmware then calls `protocol_set_mtu` with 137. 137 is the negotiated ATT MTU (payload 134 bytes).
- `GET 0x02 0xA7` reply: `02:a7:00:01:01:78:56:34:12`.
- `GET 0x02 0xB1` = **GET_WEATHER_SWITCH** (evt **316**). Reply e.g. `02:b1:aa:05:01:00:00:17:3b` (byte 2 = weather on/off: 0xAA=on, 0x55=off).

**SET 0x03 0x35 (from capture):** Payloads seen include `03:35:02:00:00:00:00:00:00:00:00:00` and `03:35:01:00:00:00:00:00:00:00:00:00`; replies include `03:35:02:00`, `03:35:01:00`, and `03:35:02:0f`. Purpose unknown (possibly newer notice/sync state). Not in the angelfit command table; keep it capture-only for now.

**Health toggles capture (`healthdata_toggles.json`):**  
The user toggled **five** features in the VeryFit app, **in this order:** (1) **Continuous HeartRate** on then off, (2) **Stress Continuous monitor** on then off, (3) **Drinking Reminder** on then off, (4) **Walk around Reminder** on then off, (5) **Menstrual Reminder** on then off. From the dump, the **commands that correspond to each** (by chronological appearance in the capture) are:

| # | App feature (user order) | Watch-side command(s) | Observed in capture (chronological) |
|---|---------------------------|------------------------|--------------------------------------|
| 1 | Continuous HeartRate on → off | **SET 0x45** | `03:45:aa:...` (on) then `03:45:55:...` (off). Single on/off pair in the toggle section (e.g. lines 1352942, 1360642). |
| 2 | Stress Continuous on → off | **None observed** | No second SET 0x45 pair and no other key toggled in that slot. Stress may be **app-only** or share 0x45 (firmware would then use the same 0x45 state for both; capture shows only one 0x45 on→off pair). |
| 3 | Drinking Reminder on → off | **SET 0x60** | `03:60:01:...` (on) then `03:60:00:...` (off). |
| 4 | Walk around Reminder on → off | **SET 0x47** | `03:47:01:...` (on) then `03:47:00:...` (off). |
| 5 | Menstrual Reminder on → off | **SET 0x41** + **0x42** | `03:41:aa:...` + `03:42:03:...` (on) then `03:41:55:...` (off); 0x42 sent immediately after each 0x41. |

Right after the **0x45** on→off pair, the app sends **GET 0x02 0x08** (`02:08`) four times (readback of HR/health state). So the sequence in the capture is: 0x45 on, 0x45 off → GET 0x08 (×4) → 0x60 on, 0x60 off → 0x47 on, 0x47 off → 0x41/0x42 on, 0x41/0x42 off.

- **Confirmed:** `0x60` (Drinking), `0x47` (Walk), `0x41`+`0x42` (Menstrual) all toggle with ACKs when the user flips those app switches.
- **Continuous HR / Stress:** The dump contains **no** `SET 0x03 0x25` (legacy HR mode) and **no** `SET 0x03 0x52` (real-time sensor) when those toggles were changed. The only other health-config key that changes state is **0x45** (payload: `03:45:aa:...` = on, `03:45:55:...` = off). So VeryFit’s **Continuous HeartRate** and/or **Stress Continuous** use this newer path; this capture does **not** show whether 0x45 is HR-only, Stress-only, or a shared “continuous monitoring” flag for both. **Cross-ref:** `hr_cont_enabled.json` confirms the same **0x45** on/off and **GET 0x08** (02:08, 4× burst) for the continuous-HR toggle.

**Continuous HR capture (`hr_cont_enabled.json`):**  
This capture is from a session where the user **toggled continuous HR** and then ended the capture. It nails the continuous-HR behaviour:

- **SET 0x45** appears in this file as well: `03:45:aa:...` (on) and `03:45:55:...` (off), matching `healthdata_toggles.json`. So **continuous HR on/off is watch-side via 0x45**.
- At the **very end** of the log (right before the user stopped the capture), the app sends **GET 0x02 0x08** (`02:08`) **four times** in a row (host → watch on 0x0AF6). No other SET commands appear in that final stretch. So when the continuous-HR toggle/screen is active, the app also uses **GET 0x08** — likely to read back the current continuous-HR (or health) config/state from the watch. The watch may reply on 0x0AF7 (not shown in the same snippet). Idowatch can send `02:08` via the “GET 0x08” button to probe the reply.

**Cross-ref `healthdata_toggles.json`:** The same continuous-HR operation (on then off) was performed there: the dump contains both **03:45:aa** (on) and **03:45:55** (off), and **GET 0x08** (`02:08`) in the same **four-times-in-a-row** burst pattern (e.g. around the 03:45 toggles). So both captures confirm **SET 0x45** for on/off and **GET 0x08** when the app is on that screen or reading back state.

**v3 (0x33) reassembly (confirmed from capture):** First packet: preamble `33 da ad da ad`, then [serial] [totalLen_lo] [totalLen_hi] [cmd_lo] [cmd_hi] [key_lo] [key_hi] [checksum…]. Copy from **offset 1** for **totalLen** bytes. Continuation packet: `33` followed by 12 bytes (often zeros), then payload; **append from offset 13 only**. A final short packet (e.g. `33 af 42`) may be checksum-only; only append when `arr.length > 13`.

**v3 cmd/key pairs observed in new_setup.json:** Activity = **0x001a / 0x0042**. First setup sweep: **0x0007 / 0x0043**, **0x0008 / 0x0044**, **0x000f / 0x0045**; after time set: **0x0007 / 0x0046**, **0x0008 / 0x0047**, **0x000f / 0x0048**; then **0x000c / 0x0049**, **0x0009 / 0x004A**, **0x0005 / 0x004B**. Later sessions continue with **0x0004 / 0x004C**, **0x0007 / 0x004D**, **0x0008 / 0x004E**, **0x000f / 0x004F**, **0x000c / 0x0050**, **0x0009 / 0x0051**, **0x0005 / 0x0052**, and a long run of **0x0004 / 0x0053** through **0x0004 / 0x0067**. A separate later sweep also uses keys **0x0002** through **0x0032**. So the earlier `0x53–0x64` note was incomplete; the highest observed key in this capture is **0x67**.

**Alarm support (SET 0x03 0x02):** The angelfit app **can set alarms on the watch**. Command is **SET 0x03 0x02** with payload **struct protocol_set_alarm** (after the 2-byte header): **alarm_id** (uint8, 0..alarm_num−1), **status** (uint8: **0xAA = on/enabled**, **0x55 = off/disabled** — angelfit uses 0xAA when syncing or deleting; new alarm default in DB is 0x55), **type** (uint8: 0=wake_up, 1=sleep, 2=sport, 3=medicine, 4=dating, 5=party, 6=meeting, 7=custom — must match func table alarm_type bits), **hour**, **minute** (uint8), **repeat** (uint8: bitmask for repeat days, or 0xFF for “all days” in sync), **tsnooze_duration** (uint8: snooze duration in minutes). The **func table** (GET 0x02 0x02) gives **alarm_num** (max alarms) and **alarm_type** (which types the watch supports). The iOS app syncs alarms by: (1) `protocol_set_alarm_clean()`, (2) `protocol_set_alarm_add(alarm)` for each alarm from DB, (3) `protocol_set_alarm_start_sync()` — firmware sends them one-by-one with 50 ms between packets, waiting for BLE reply each time. To set a single alarm from idowatch you would send one packet: `[0x03, 0x02, alarm_id, status, type, hour, minute, repeat, tsnooze_duration]` (7 bytes after cmd/key). The idowatch htmlapp now has an **Alarms** section: set single alarm (slot, on/off, type, time, repeat, snooze) and **full alarm sync** (add multiple alarms to a list, then sync all to the watch with 300 ms between each).

**Alarm options (per-alarm and global):** The following options match the IDO GitBook and wire format. **Per alarm:** (1) **Time** → `hour`, `minute` (SDK and wire; v3 payload e.g. `04 19` = 4:19). (2) **Days of week to repeat** → `repeat`: bitmask [Monday … Sunday]; **0 = no repeat**, 0xFF = every day (legacy SET 0x02 and v3). **All alarms (global / per-alarm in SDK):** (3) **Remind me interval time later** (snooze) → `tsnoozeDuration` (SDK: snooze duration in minutes); v3 also has **delayMinute**. Default 10 minutes. (4) **Repeats of reminder** (how many times to remind after the first) → **repeatTime** (v3 only; SDK: "Repeat alarm times"). Default 1 time. Legacy SET 0x02 has only `tsnooze_duration` (snooze minutes); v3 alarm blocks in cmd 0x0E include repeat, delayMinute, repeatTime (see `logcat_dumps/set_alarms_and_sports.txt`: per-alarm bytes after hour/minute e.g. `01 00 0A 00 01` consistent with repeat, 0x0A = 10 min delay, 1 repeat). Summary: **Time** = hour, minute; **Days repeat (0 = no repeat)** = repeat; **Remind interval (default 10 min)** = tsnoozeDuration / delayMinute; **Repeats of reminder (1 time)** = repeatTime (v3).

**Heart rate enable/disable (angelfit):** The protocol has an explicit on/off via **SET 0x03 0x25** (heart rate mode). Payload is one byte: **0x55 = close (HR off)**, **0x88 = auto (continuous monitoring on)**, **0xAA = manual (manual measurement on)**. Source: `angelfit/AngelFit/Protocol_c/protocol.h` (`struct protocol_heart_rate_mode`), `protocol_exec.c` (VBUS_EVT_APP_SET_HEART_RATE_MODE), `CoreDataHandler.swift` default `heartRateMode = 0x88` with comment "auto:0x88 close:0x55 manual:0xAA". GET 0x02 0x20 returns heart rate sensor params (rate, led_select). SET 0x03 0x24 sets HR alert thresholds (burn_fat, aerobic, limit); SET 0x03 0x52 sets real-time sensor stream status (gsensor_status, heart_rate_sensor_status). Only supported if func table reports heart_rate (main_func bit 5) or heart_rate_monitor (ohter2 bit 3). **Sync order in angelfit:** config sync sends SET_HEART_RATE_MODE only when **ohter2.heartRateMonitor** is true (ohter2 bit 3); SET_HEART_RATE_INTERVAL is also in the sync list. Some firmware may require **SET 0x03 0x24** (heart rate interval: burn_fat, aerobic, limit thresholds, e.g. 135, 96, 160) to be sent before SET 0x03 0x25 (mode). The idowatch "Start continuous HR" sequence sends interval → mode → real-time stream, with 600 ms delays between commands. **Important limit:** `healthdata_toggles.json` does **not** show VeryFit using `0x25` for its own continuous-health toggles on this watch, so `0x25` remains a useful manual / angelfit-style control, not a confirmed mirror of the VeryFit UI flow.

**Heart rate troubleshooting (auto HR not activating):** (1) **Func table:** Ensure GET 0x02 0x02 shows **main_func bit 5 (heart_rate)** and **ohter2 bit 3 (heart_rate_monitor)** set; otherwise the watch may ignore SET 0x25. (2) **Order and delays:** Try **Alternative order** in idowatch: enable real-time HR stream (SET 0x52, HR byte 0xAA) *first*, then SET 0x24 (interval), then SET 0x25 (mode 0x88), with 600 ms between each. Some devices only apply mode when the sensor stream is already on. (3) **Mode byte:** Angelfit uses **0x55/0x88/0xAA**; the IDO SDK v2 model uses numeric modes **0=off, 1=manual, 2=automatic, 3=continuous**. If 0x88 does nothing, try sending mode byte **2** (SET 0x03 0x25 0x02) via "Heart rate: on (v2 byte 2)". (4) **Interval first:** Always send SET 0x03 0x24 (e.g. 135, 96, 160) before or in the same sequence as SET 0x25; some firmware ignore 0x25 until interval is set.

**Sleep (goal + data / REM stages):** **SET 0x03 0x04** sets the **sleep goal** (target duration): payload **struct protocol_set_sleep_goal** = **hour**, **minute** (2 bytes). Only supported if func table **main_func sleep(1)** is set. **Sleep data** can be requested in two ways:

- **Legacy (angelfit):** **HEALTH_DATA** cmd **0x08**, key **0x04** (today) or **0x06** (history): `0x08 0x04 0x01` / `0x08 0x06 0x01`. The watch may stream multi-packet sleep data on 0x0AF7. Payload format (e.g. 8-minute bins or segments: awake/light/deep/REM) is device-specific; idowatch implements this and logs raw sleep packets.
- **v3 health sync (A200 / VeryFit):** The **logcat_dumps** show that VeryFit syncs sleep via **v3 health data**, not legacy 0x08. In `logcat_dumps/ui_watch_face_write_json.txt` the app runs a v3 health sync sequence including **data_type 7** (`PROTOCOL_V3_HEALTH_DATA_TYPE_SLEEP`): **v3 cmd 0x04** with payload operate=0 (start) then operate=1 (stop), data_type=7. Example TX: start `33 DA AD DA AD 01 10 00 04 00 5F 01 00 07 00 00 00 2F 8D`, stop `33 DA AD DA AD 01 10 00 04 00 60 01 01 07 00 00 00 1A F4`. Watch reply: 65-byte packet (head_size 40, item_count 0 in that capture). There is **no dedicated sleep-only logcat dump**; the evidence is the v3 health sync run during watch face upload.

**v3 docs vs logcat for sleep:** The **IDO GitBook** documents only **Sleep v2** (https://idoosmart.github.io/IDOGitBook/en/query/IDOQuerySleepFunction_v2.html): high-level API (query by year/month/week/day, `IDOSyncSleepDataInfoBluetoothModel` with totalMinute, lightSleepMinute, deepSleepMinute, sleepItems, etc.). It does **not** document v3 sleep wire format or that sleep uses v3 cmd 0x04 + data_type 7. So **trusting only the v3 docs** does not tell you how to sync sleep on the wire; the docs are v2 and do not describe the v3 health-sync packet layout. **From our logcat_dumps**, sleep on the A200 is **v3 health sync (cmd 0x04, type 7)**; the legacy path (0x08 0x04/0x06) may still work on older firmware or different devices, but for this device the app uses v3. To implement sleep sync that matches VeryFit on the A200, use v3 cmd 0x04 with data_type 7 (start/stop) and parse the v3 reply (40-byte header, optional item payload); the GitBook v2 model (totalMinute, lightSleepMinute, etc.) can still be used to interpret the parsed data once the wire format is reversed from the 40-byte header and any item blocks.

**Unified v3 health sync (HR, SpO2, sleep, sport, etc.):** The same run in `logcat_dumps/ui_watch_face_write_json.txt` shows **one pattern** for all health data: **v3 cmd 0x04** (health data sync) with a **data_type** byte. Request format: send **start** (operate=0) then **stop** (operate=1); payload after the v3 header (length 0x10, cmd 0x04, nseq) is **operate (1B) | data_type (1B) | flags (2B) | offset (2B)** then CRC. So we can **guess** HR, SpO2, pressure, activity, swim, sleep, and sport from the same pattern by changing only **data_type**:

| data_type | Name (from dump) | Example TX start (nseq varies) |
|-----------|------------------|--------------------------------|
| **1** | SpO2 (PROTOCOL_V3_HEALTH_DATA_TYPE_SPO2) | `33 DA AD DA AD 01 10 00 04 00 57 01 00 01 01 00 00 2B 0E` |
| **2** | Pressure / stress (PROTOCOL_V3_HEALTH_DATA_TYPE_PRESSURE) | `33 DA AD DA AD 01 10 00 04 00 59 01 00 02 01 00 00 7F A7` |
| **3** | HR (PROTOCOL_V3_HEALTH_CMD_TYPE_HR) | `33 DA AD DA AD 01 10 00 04 00 65 01 00 03 01 00 00 2D DA` |
| **4** | Activity (PROTOCOL_V3_HEALTH_DATA_TYPE_ACTIVITY) | `33 DA AD DA AD 01 10 00 04 00 5B 01 00 04 00 00 00 35 D7` |
| **6** | Swim (PROTOCOL_V3_HEALTH_DATA_TYPE_SWIM) | `33 DA AD DA AD 01 10 00 04 00 5D 01 00 06 00 00 00 78 9B` |
| **7** | Sleep (PROTOCOL_V3_HEALTH_DATA_TYPE_SLEEP) | `33 DA AD DA AD 01 10 00 04 00 5F 01 00 07 00 00 00 2F 8D` |
| **8** | Sport (PROTOCOL_V3_HEALTH_DATA_TYPE_SPORT) | `33 DA AD DA AD 01 10 00 04 00 61 01 00 08 01 00 00 F4 05` |

Stop packet: same structure with operate=**01** and next nseq; CRC changes. Reply layout (head_size, data_size, item_count) varies by type (e.g. sleep head 40, HR head 29, sport can carry 960-byte payload). So **yes** — we can guess HR, SpO2 (O2), pressure/stress, activity, swim, sleep, and sport from this single pattern; only the **data_type** byte and nseq/CRC differ. Types 0, 5, 9+ may exist on other firmware; the dump only shows 1–4, 6–8.

**V3 sport summary reply (data_type 8)** — Observed from **confirmed-only.html** and a real sync (2026-03-08):

- **TX:** `33 DA AD DA AD 01 10 00 04 00 61 01 00 08 01 00 00 F4 05` (19 B). Same as the sport row in the table above (cmd 0x04, data_type 8, operate 0 start).
- **RX:** Multi-packet v3 reply. First packet 137 B (preamble + payload), continuation packets `33 00 00 00 00…` (12-byte cont header then payload). Example total reassembled payload: **391 bytes** (136 + 136 + 119 after v3 length/continuation handling).
- **Common header** (from first packet payload): **dataType 8**, **headSize 36**, **itemCount 33**, **dataSize 330**. So the reply has a 36-byte sport-specific header and 330 bytes of item data.
- **Sport summary header** (36 bytes, parsed by `parseV3SportSummary`): version (1 B), year (2 LE), month (1), day (1), minuteOffset (2 LE), intervalMinutes (1), steps (4 LE), rawTotalCalories (4 LE), totalDistance (4 LE), totalActiveTime (4 LE), headerItemCount (2 LE), headerDisplayCalories (2 LE). **coveredUntil** (minutes of day) = minuteOffset + (itemCount × intervalMinutes).
- **Item data:** 33 slots of **intervalMinutes** (e.g. 15) each; each slot can hold steps/calories/distance for that window. **nonZeroItems** is the list of slots with non-zero activity (can be empty early in the day).
- **Example parsed:** date 2026-03-08, interval 15 m, offset 0, 33 items, steps=94, kcal=68 (headerDisplayCalories 68, rawTotalCalories 368), distance=72, coveredUntil=08:15. So “Daily sport summary” in the app is this v3 health type 8 reply; it is the path VeryFit uses for steps/kcal/distance for the current day.

**Weather support:** The protocol supports weather only if the **func table** reports it (byte "ohter" bit 7 = weather). Two commands exist: (1) **SET 0x03 0x2D** (set weather switch) with payload cmd1, cmd2, cmd3 — typically cmd1=1 to enable, 0 to disable. (2) **WEATHER 0x0A 0x01** (set weather data) with **struct protocol_weatch_data**: after the 2-byte header (0x0A 0x01), 7 bytes (today_type, today_tmp, today_max_temp, today_min_temp, humidity, today_uv_intensity, today_aqi) and 3×3 bytes for future[3] (each: type, max_temp, min_temp). So the app can enable/disable the weather feature and push current (and optional forecast) weather to the watch.

**Func table (GET 0x02 0x02):** The **function table** is a **device capability bitmap**. When the app sends **Get func table** (0x02 0x02), the watch replies with **struct protocol_get_func_table**: after the 2-byte header (0x02 0x02), **15 bytes** in order:

| Offset | Field        | Meaning (bits = flags) |
|--------|--------------|--------------------------|
| 0      | main_func    | Main: sport(0), sleep(1), single_sport(2), live_data(3), OTA(4), heart_rate(5), ANCS(6), timeline(7) |
| 1      | alarm_num    | Number of alarms supported (0–255) |
| 2      | alarm_type   | Alarm types: wake_up(0), sleep(1), sport(2), medicine(3), dating(4), party(5), meeting(6), custom(7) |
| 3      | control      | Control: photo(0), music(1) |
| 4      | call         | Call: incoming(0), contacts(1), id(2) |
| 5      | msg          | Notify: SMS(0), mail(1), QQ(2), WeChat(3), Weibo(4), Facebook(5), Twitter(6) |
| 6      | ohter        | Other: long_sit(0), lost_find(1), one_key_SOS(2), find_phone(3), find_device(4), config_default(5), up_hand_gesture(6), weather(7) |
| 7      | msg_config   | SMS config: show_contacts(0), show_id(1), show_content(2) |
| 8      | msg2        | Notify2: WhatsApp(0), Messenger(1), Instagram(2), LinkedIn(3), calendar(4), Skype(5), alarm_clock(6), Pokeman(7) |
| 9      | ohter2       | Other2: static_HR(0), do_not_disturb(1), display_mode(2), heart_rate_monitor(3), … |
| 10     | sport_type1  | Sport: walk(0), run(1), bike(2), on_foot(3), swim(4), mountain_climbing(5), badminton(6), other(7) |
| 11     | sport_type2  | Fitness(0), spinning(1), ellipsoid(2), treadmill(3), sit_up(4), push_up(5), dumbbell(6), weightlifting(7) |
| 12     | sport_type3  | Bodybuilding(0), yoga(1), rope_skipping(2), table_tennis(3), basketball(4), football(5), volleyball(6), tennis(7) |
| 13     | sport_type4  | Golf(0), baseball(1), skiing(2), roller_skating(3), dance(4), walk(5) |
| 14     | main_func1   | e.g. log_in(0) |

The app uses this to show/hide features (e.g. only offer “Find phone” if find_phone bit is set), show alarm count, and know which notification and sport types the device supports. See `protocol_func_table.c` and `protocol_func_table.h` in angelfit for the full bit definitions.

**Firmware protocol source (Realtek/IDO):**

- **protocol.h** — Command codes: CMD_GET=0x02, CMD_SET=0x03, CMD_MSG=0x05; KEY_GET_DEVICE_INFO=0x01, KEY_SET_NOTIF=0x30, KEY_MSG_CALL=0x01, **KEY_MSG_CALL_STATUS=0x02**, KEY_MSG_MSG=0x03; struct protocol_set_notice (notify_switch, call_switch, call_delay), protocol_msg_call (total, serial, data[16]), protocol_msg_call_content (phone_number_len, contact_len, data), **protocol_msg_call_status (status)**.
- **protocol_send_notice.c** — Call/SMS send: 16-byte payload chunks; call first payload = notice_call_head (phone_number_length, contact_length) + phone + contact; SMS first payload = notice_msg_head (type, data_length, phone_number_length, contact_length) + phone + contact + data. PROTOCOL_NOTICE_ONE_PACK_SZIE = 16.

**IDO SDK (GitBook) — set/notification-related:**

- https://idoosmart.github.io/IDOGitBook/en/ — IDO SMART BAND SDK (preface).
- https://idoosmart.github.io/IDOGitBook/en/IDOBluetooth.html — Bluetooth Management Library.
- https://idoosmart.github.io/IDOGitBook/en/IDOSetUpFunction.html — Set command function overview (list of set APIs).
- https://idoosmart.github.io/IDOGitBook/en/set/IDOSetNoticeFunction.html — Set smart reminder (enable which app notifications are forwarded; no raw packet format).
- https://idoosmart.github.io/IDOGitBook/en/set/IDOSetNoticeStateFunction.html — Set v3 smart reminder (notification status per app).
- https://idoosmart.github.io/IDOGitBook/en/set/IDOSetNoticeStateFunction.html — Set v3 smart reminder (third-party app notification state).
- https://idoosmart.github.io/IDOGitBook/en/set/IDOSetFindPhoneFunction.html — Set find phone.

**Other projects / examples:**

- https://github.com/idoosmart/Flutter_Demo — IDO Flutter SDK demo.
- https://www.b4x.com/android/forum/threads/send-ble-alert-to-smart-band-mi-band-5.138022/ — Sending BLE alert to Mi Band 5 (header 0x05 0x01 + UTF-8; different vendor, used as a format guess).
- https://medium.com/fmisec/heres-how-i-send-a-notification-to-smart-band-77f835b33d90 — Send notification to smart band (M4, Mi Band 3): nRF 0x2a46 value first byte 01=Email, 03=Call, 04=Missed Call, 05=SMS/MMS; then count; then message.
- https://colmi.puxtril.com/commands/ — Colmi BLE API: command 114 “3rd Party Push Message”, PushMessageSource enum (SMS=1, QQ=2, WeChat=3, PhoneAction=4, Facebook=5, WhatsApp=6, Twitter=7, Skype=8, Line=9).
- https://0110.be/posts/Access_Mi_Band_from_Android_-_Notes_on_the_Bluetooth_LE_Protocol — Mi Band BLE protocol notes (older firmware).

### Watch face upload (VeryFit / .iwf)

VeryFit can send custom watch faces to the watch. The flow (from user reports, e.g. Ksix Compass) is:

1. **Source:** Watch faces are stored under the app as **.zip** files (e.g. in `/data/data/com.watch.life/files/Veryfit/dial/7733/` on Android). The server sends .zip (e.g. cw1.zip, w24.zip); VeryFit unzips and shows the folder.
2. **Build:** When sending to the watch, VeryFit builds **ido_watch_plate_data.iwf** from the unzipped folder (binary of all elements), then compresses it to **ido_watch_plate_data.iwf.lz**.
3. **Send:** The **.iwf.lz** file is sent to the watch over BLE.

**BLE path:** The **bulk write** characteristic is **0x0AF1** (angelfit: `bigWrite`; used there for health data sync). VeryFit likely uses 0x0AF1 for watch face payload; a control command on **0x0AF6** may be sent first to start the transfer (exact command unknown). TOOBUR section "Command Center" describes 0x0AF6 and 0x0AF1 as control vs bulk data.

**Transfer format (from reverse engineering):** The data sent is **not** a single LZ stream. It is **chunked blocks** with a **4-byte length prefix** before each block (little-endian), then the raw data for that block:

```
<block length (4 bytes)><data block><next block length (4 bytes)><data block>...<last block length (4 bytes)><data block>
```

So the .iwf.lz file (or the payload VeryFit sends) is this block-prefixed format; the per-block data may be compressed (e.g. LZ-like) and is **device-specific**.

**.iwf format:** The .iwf (pre-compression) is a container with simple headers and offset/length block descriptions; frames are often RGB565 or RGB565 + 4-bit alpha. It can be unpacked into JSON config and images (PNG, etc.). Different models (IDW13, IDW19, Ksix Compass, etc.) may expect different resolutions or formats.

**Compression:** The .iwf.lz compression is **not** standard LZ; it is custom and may vary by device. Users report trying LZ4, ZIP, or uncompressed and the watch may ACK every ~10 packets but the face does not appear—so the exact compression matters. For some devices "compression format 2" is mentioned. To reproduce, you need the exact file content (from app cache or server response for your watch model), then match the compression and chunking.

**Existing work:**

- **GadgetBridge** has been extended with watch face upload support for at least one model (e.g. **Ksix Compass**), including building .iwf, compressing to .iwf.lz, and sending over BLE.
- **CadranEditor** (Qt/C++, by sptech38): creates 240x240 watch faces for Ksix Compass, builds .iwf, compresses to .iwf.lz, and can send via GadgetBridge.
- **VeryWatchTool / IWFmake** (CoolSteel712): editors for IDW19 and others; .iwf/.zip creation; ".iwf.lz creation" was planned.
- XDA threads: Need help making my own watch faces in .iwf format (Veryfit Watch Face Format); IWF Editor for Milouz IDW19; UPDATED Local Watch Face App.

**Practical approach:** To implement upload for a specific watch: (1) Sniff VeryFit BLE traffic (nRF Connect or HCI snoop) while sending a known watch face; (2) Capture the exact file from app cache or server for that model; (3) Match the chunking (4-byte length + blocks) and compression; (4) Send via 0x0AF1 (and any start/end commands on 0x0AF6 if present in the capture).

### GadgetBridge and angelfit-like (IDO / 0x0AF0) devices

**Does GadgetBridge support angelfit/IDO/VeryFit (0x0AF0) devices?**  
**No.** Mainline GadgetBridge does not include a device coordinator or protocol implementation for the IDO/Realtek 0x0AF0 service (angelfit protocol). **GloryFit** support in GadgetBridge is a **different** protocol (different GATT services; not 0x0AF0). So watches that use VeryFit/angelfit (e.g. Ksix Compass, many IDO-based brands) are not supported out of the box.

**Ksix Compass:** There is an open **device request** ([issue #3487](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/3487)) for Ksix Compass with no implementation yet. Some users (e.g. sptech38 on XDA) have added Ksix support in **private forks** (e.g. with CadranEditor for watch face upload); that work is not merged upstream.

**How to try to get angelfit-like devices working in GadgetBridge:**

1. **Reference the protocol**  
   Use idowatch and the angelfit repo as the protocol reference: service **0x0AF0**, write **0x0AF6**, notify/read **0x0AF7**, bulk write **0x0AF1**, bulk read **0x0AF2**. TOOBUR.md and the angelfit `protocol.h` / `protocol_write.c` define GET/SET/MSG commands and payloads.

2. **Follow the new-gadget tutorial**  
   - [New gadget tutorial](https://gadgetbridge.org/internals/development/new-gadget/)  
   - Add a **device type** in `DeviceType` and a **DeviceCoordinator** (e.g. `AngelfitDeviceCoordinator` or `IDODeviceCoordinator`) that:
     - Returns a name pattern matching your watch (e.g. `Pattern.compile("Ksix.*|IDW.*|...", Pattern.CASE_INSENSITIVE)` if you know the advertised names).
     - Uses **BLE scan filters** for service UUID **0x0AF0** so only these devices are discovered.
     - Implements `getBondingStyle()` (e.g. `BONDING_STYLE_BOND` for BLE pairing).
     - Declares supported features via `supportsXXX()`.
   - Implement **DeviceSupport** extending `AbstractBTLESingleDeviceSupport` (or `AbstractBTLEMultiDeviceSupport` if needed). Use `Transaction` and `BtLEQueue` for GATT: connect, discover 0x0AF0/0x0AF6/0x0AF7 (and 0x0AF1/0x0AF2 if you do bulk transfer), enable notifications on 0x0AF7, then send commands (e.g. GET 0x02 0x01 for device info) and parse replies to mark the device initialized.

3. **Implement initialization and features**  
   In `initializeDevice()`: send GET device info (0x02 0x01), optionally GET func table (0x02 0x02), set time (0x03 0x01), etc. Map protocol replies to GadgetBridge’s device state and database (e.g. battery, firmware, activity sync). Reuse the command bytes and parsing from idowatch/angelfit (GET/SET/Control/MSG as in TOOBUR command table).

4. **Optional: device request and docs**  
   File a [device request](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/new?template=.gitea%2fissue_template%2fdevice_request.yml) on Codeberg and link TOOBUR.md (or a short protocol summary) so maintainers can see the protocol. Contributing a full or partial implementation (e.g. discovery + device info + time sync + activity sync) as a PR is the way to get angelfit-like devices into mainline GadgetBridge.

5. **Bluetooth inspection**  
   Use [Inspect Bluetooth packets](https://gadgetbridge.org/internals/development/bluetooth/) and nRF Connect or HCI snoop to confirm your watch uses 0x0AF0 and matches the angelfit command set before coding.
