# LATEST_SYNC_PARSING.md

## Where to read what (canonical split — avoid duplicating stale details)

| Location | Use for |
|----------|---------|
| **`LATEST_SYNC_PARSING.md` (this file)** | **Wire layout**, v3 BLE reassembly rules, HTML tool parsers, and **§11–13** = exact **Gadgetbridge** sync route (classes + GATT + prefs). Prefer this for “how bytes work.” |
| [`README.md`](README.md) | Short **user-facing** feature list, global Gadgetbridge auto-fetch, links to deeper docs. |
| [`gadgetbridge/README_TOOBUR.md`](gadgetbridge/README_TOOBUR.md) | Gadgetbridge **file map** + feature table (keep in sync with §11 here; do not re-spec full packet layouts there). |
| [`TOOBUR.md`](TOOBUR.md) | Protocol background, VeryFit vs angelfit, long logcat narratives. |

If anything disagrees, **this file + `TooburV3HealthSync` / `TooburV3FetchHealthOperation` / `TooburSupport`** win for Gadgetbridge behavior.

---

## Scope
Documenting what we currently know (from the HTML implementations under `htmlapp/` and from **`gadgetbridge/` TOOBUR support**) about TOOBUR / VeryFit **v3 health** sync — **not** “v5” (there is no separate v5 health layer in this repo; native logs sometimes refer to **protocol v3** families). This file covers:

- **v3 cmd `0x04`** (“health data sync”) replies and parsing
- **v3 cmd `0x05`** (“health sizes by offset”) requests and replies
- How **Gadgetbridge** triggers sync vs **GET live data** (`0x02` `0xA0`)

Topics covered from HTML:
- v3 BLE reassembly rules
- the shared “health common header” inside `0x04` replies
- per-`dataType` parsing we implemented:
  - `dataType == 3` (HR day data) in `toobur-hr-csv.html`
  - `dataType == 4` (activity / workout record) in `confirmed-only.html`
  - `dataType == 7` (sleep summary) in `confirmed-only.html`
  - `dataType == 8` (sport summary / steps summary) in `confirmed-only.html`

Source files:
- `htmlapp/toobur-hr-csv.html`
- `htmlapp/confirmed-only.html`

---
## 1) v3 over BLE: framing + reassembly
Both HTML apps treat v3 messages as a logical payload that may be split across multiple BLE notifications. The reassembly logic is implemented in:
- `toobur-hr-csv.html`: `handleV3ReplyReassembly(arr)` + `dispatchV3Reply(buffer)`
- `confirmed-only.html`: `handleV3ReplyReassembly(arr)` + `dispatchV3Reply(buffer)`

### 1.1 Detecting the first packet vs continuation packets
When a BLE notification arrives:
1. **First v3 packet** is recognized when:
   - `arr[0] == 0x33`
   - and `arr[1..4] == DA AD DA AD`
   - and `arr.length` is large enough to contain the v3 header fields (apps require `>= 10`).
2. **Continuation packets** are recognized when:
   - we are currently assembling (`rx_buffer` exists)
   - and the packet begins with `0x33`
   - but it does NOT match the “full preamble” pattern `33 da ad da ad ...`.

### 1.2 Total length calculation (how much to reassemble)
Both apps obtain the logical v3 message total length from the first packet using:
- `totalLen = getV3FirstPacketTotalLen(arr)`

In `toobur-hr-csv.html`:
- `getV3FirstPacketTotalLen(arr)` returns `arr[6] | (arr[7] << 8)`

So: bytes `[6..7]` of the v3 header encode the logical total length for reassembly.

### 1.3 How bytes are copied into the receive buffer
In both apps:
- For the **first packet**, the code creates `rx_buffer = new Uint8Array(totalLen)` and starts by copying the v3 bytes from the BLE packet while skipping the first BLE byte:
  - `rx_buffer[0..]` receives `arr.subarray(1)` (i.e., drop the leading `0x33` byte that appears as the BLE-chunk prefix).
- For **continuation packets**, the code copies:
  - `arr.subarray(1)` into the next offset of `rx_buffer`.

Once `rx_written === rx_buffer.length`, the app calls `dispatchV3Reply(rx_buffer)` and resets rx state.

---
## 2) Shared v3 cmd `0x04` reply layout inside the payload
After reassembly, the apps parse:
- `cmd` from the v3 header
- `seq` from the v3 header
- `payload` as bytes after the fixed v3 header portion.

### 2.1 Where `cmd` and `seq` are read
In `toobur-hr-csv.html` (`dispatchV3Reply(buffer)`):
- `cmd = parseUint16LE(buffer, 7)`
- `seq = parseUint16LE(buffer, 9)`
- `payload = buffer.subarray(11)`

### 2.2 Health “common header” parsing (payload bytes 0..13)
Both apps use a shared parser:
- `parseV3HealthCommon(payload)`

It returns:
- `operate = payload[0]`
- `dataType = payload[1]`
- `flag1 = payload[2]`
- `flag2 = payload[3]`
- `flag3 = payload[4]`
- `itemCount = parseUint16LE(payload, 5)`
- `headSize = parseUint16LE(payload, 7)`
- `dataSize = parseUint32LE(payload, 9)`
- `reserved = payload[13]`

Then the app slices:
- `headerStart = 14`
- `headerBytes = payload.slice(headerStart, headerStart + headSize)`
- `dataBytes = payload.slice(headerStart + headSize, headerStart + headSize + dataSize)`

Both apps include bounds checks using `Math.min(...)` to avoid overruns.

---
## 3) Request side (how we build v3 cmd `0x04` packets)
The request builder exists in `toobur-hr-csv.html`:
- `buildV3HealthSync04(operate, dataType)`

It constructs a 19-byte v3 packet:
- v3 preamble: `33 DA AD DA AD`
- v3 version/length bytes are hard-coded:
  - `packet[5] = 0x01`
  - `packet[6] = 0x10`
  - `packet[7] = 0x00`
- v3 cmd/key:
  - `packet[8] = 0x04`
  - `packet[9] = 0x00`
- `seq` is taken from `nextV3Seq()` and written into `packet[10..11]` (LE)
- `operate` is written into `packet[12]`
- `dataType` is written into `packet[13]`
- remaining bytes:
  - `packet[14]` — in **`toobur-hr-csv.html`** this is hard-coded **`0x01`** for all types; native/VeryFit-style clients use **`0x01` for “day data” types and `0x00` for “count data” types** (activity / swim / sleep). See **§3.1.1a**.
  - `packet[15..16]` — **save offset** LE (`saveOffset16`; often `0` for a full baseline sync).
- CRC-16 CCITT FALSE:
  - computed over `packet` bytes `[1 .. packet.length-3]`
  - stored into the last two bytes `packet[17..18]` as LE.

Operationally, the code expects the device to respond to:
- start packet: `operate = 0`
- stop packet: `operate = 1`

---
## 3.1) v3 health sizes (cmd `0x05`)
Both HTML apps also understand v3 cmd `0x05`:
- `confirmed-only.html`: when `cmd === 0x0005`, it reads `totalBytes` from the reply payload as:
  - `totalBytes = parseUint32LE(payload, 0)`
- `toobur-hr-csv.html`: when `cmd === 0x0005`, it does the same and logs:
  - total sync bytes across the queried type set (used to estimate how many BLE packets the watch will stream)

In the UI, `cmd 0x05` is used as a “how much data is stored” probe before issuing `cmd 0x04` start/stop sync requests.

Current implementation note:
- `toobur-hr-csv.html` now builds `0x05` dynamically using the inferred record format
  - `typeId (1 byte) + savedOffset LE32 (4 bytes)`
- and, because that page is HR-focused, it currently sends an **HR-only** record:
  - `03 00 00 00 00`

### 3.1.1) Important log evidence from `reinstall_app_bind_full.txt`
The strongest capture-backed summary of the v3 health families currently known to this firmware is the cluster:
- `reinstall_app_bind_full.txt` lines `1936..1942`

Those lines show the firmware’s sync scheduler enumerating these health sync types:
- `0x01` -> `PROTOCOL_V3_HEALTH_DATA_TYPE_SPO2`
- `0x02` -> `PROTOCOL_V3_HEALTH_DATA_TYPE_PRESSURE`
- `0x04` -> `PROTOCOL_V3_HEALTH_DATA_TYPE_ACTIVITY`
- `0x06` -> `PROTOCOL_V3_HEALTH_DATA_TYPE_SWIM`
- `0x07` -> `PROTOCOL_V3_HEALTH_DATA_TYPE_SLEEP`
- `0x08` -> `PROTOCOL_V3_HEALTH_DATA_TYPE_SPORT`
- `0x03` -> `PROTOCOL_V3_HEALTH_CMD_TYPE_HR`

So for this firmware/build, these are the core v3 health sync IDs that the native code considers during the sync run.

### 3.1.1a) Day data vs count data (vendor log labels; incremental sync semantics)

Native scheduler logs sometimes tag each type in one of two ways, for example:

- `v3 health sync type:0x01 … [day data, save data offset:0]`
- `v3 health sync type:0x04 … [count data]`

This is **about how the firmware keys incremental sync for that stream**, not about whether a **`0x04` reply** “returns days” or “returns counts.” Replies still carry whatever that type’s layout defines (including `itemCount`, dates, etc., as in §2).

**Day data** (`[day data, save data offset:…]`)

- Storage is **organized by calendar day** (day-oriented stream).
- The **save data offset** in the log is **where to resume** in that day-oriented stream: the same field as **bytes 15–16 LE** (`saveOffset16`) on **cmd `0x04`** requests, and the **per-type 32-bit offset** in **`0x05`** “sizes” queries (`typeId` + 4-byte LE offset per entry).

**Count data** (`[count data]`)

- Storage is **not** framed as “one logical row per calendar day” in the same way; it is **record-oriented** (discrete records: activity chunks, swim sessions, sleep segments, etc.).
- The **same** offset fields still mean **position in the stored byte stream** for that type, but the firmware treats the stream as **count-indexed** (record-ordered) rather than **day-indexed**.

**Types (typical vendor mapping)**

| Label | Health `dataType` values |
|--------|---------------------------|
| Day data | `0x01` SpO2, `0x02` pressure, `0x03` HR, `0x08` sport |
| Count data | `0x04` activity, `0x06` swim, `0x07` sleep |

**Wire note (cmd `0x04`, byte 14):** In Gadgetbridge, `TooburV3HealthSync.defaultByte14ForDataType` sets **`0x00`** for activity / swim / sleep (`0x04`, `0x06`, `0x07`) and **`0x01`** for the day-data types above. That matches VeryFit TX examples in `TOOBUR.md` (e.g. activity `… 04 00 …`, sport `… 08 01 …`). The HTML tool `toobur-hr-csv.html` historically hard-codes `packet[14] = 0x01` for all types; a full client should follow the day/count split for firmware compatibility.

### 3.1.2) Observed `0x05` request payload shape
Immediately after those scheduler lines, the same capture shows the outgoing `cmd 0x05` frame:
- `reinstall_app_bind_full.txt` line `1948`

Observed TX payload bytes after `cmd=0x05` and `nseq`:

```text
01 00 00 00 00 02 00 00 00 00 08 00 00 00 00 03 00 00 00
```

The most useful way to read this is **not** as aligned u32 words. The non-zero bytes occur every 5 bytes, which strongly suggests a repeating record shape:
- `typeId` (1 byte)
- `saveOffset` / `syncOffset` (4 bytes)

So the observed payload begins as:
- `01 00 00 00 00` -> type `1`, offset `0`
- `02 00 00 00 00` -> type `2`, offset `0`
- `08 00 00 00 00` -> type `8`, offset `0`
- `03 00 00 00 ...` -> type `3`, offset `0`

This matches the nearby scheduler log wording:

- `v3 health sync type:0x.. [day data,save data offset:..]`

See **§3.1.1a** for what **day data** vs **count data** means (incremental sync addressing — not the same as `itemCount` in a reply).

It also matches an older capture pattern where some entries had non-zero saved offsets (for example type `2` and `8`), which would naturally fit a `type + offset` record encoding.

### 3.1.3) Current interpretation of the `0x05` request list
Current best interpretation from this capture:
- the `0x05` request is **not simply a blank probe**
- it contains an explicit list of health records to be counted
- each record is best interpreted as:
  - `typeId` (1 byte)
  - `savedOffset` (4 bytes LE)
- the **observed** records in that run are a **subset** (types `1`, `2`, `8`, `3` only in the snippet)

Important nuance:
- even though the scheduler lines show support for `4`, `6`, and `7`, that particular `0x05` TX **did not** include those IDs
- therefore, on the wire, `0x05` is a **selectable query list** — the app can ask for any subset and pass non-zero offsets per type for incremental “bytes since last sync” style queries

**Gadgetbridge (`TooburV3HealthSync.buildV3HealthSizesRequest`)** uses a **fixed full list** of seven types in VeryFit order:  
`0x01, 0x02, 0x03, 0x04, 0x06, 0x07, 0x08`  
(all offsets `0` for a full baseline, or sport-only offset mode via prefs — see §11). That matches the “efficient sync” design (count aggregate bytes, then `0x04` start/stop per type) even when a one-off phone capture shows a shorter list.

This means:
- `sync_timer_handles` lines tell us what the firmware health sync machinery supports / schedules
- a given `0x05` TX shows **which types + offsets** that client chose to include in the size sum

### 3.1.4) Sleep and the `0x05` query list
Some **phone captures** show a **short** `0x05` list (e.g. only types `1`, `2`, `8`, `3`) while the native scheduler still *mentions* types `4`, `6`, `7` — see §3.1.3. Adding sleep to a minimal list would be a **5-byte record** `07 00 00 00 00`.

**Gadgetbridge** does not use a short list: `TooburV3HealthSync.buildV3HealthSizesRequest` always emits **all seven** types in `V3_HEALTH_SYNC_DATA_TYPES` order (`0x01` … `0x08` including **`0x07` sleep**), with per-type offsets (default `0`, optional sport offset via prefs). The HTML tools may still use HR-only or partial lists for experiments.

---
## 4) dataType mapping implemented in the HTML apps
`confirmed-only.html` provides this name map:
- `1` -> `SpO2`
- `2` -> `Pressure`
- `3` -> `Heart rate`
- `4` -> `Workout record`
- `6` -> `Swim`
- `7` -> `Sleep`
- `8` -> `Sport summary`

Inside `confirmed-only.html`, only `dataType` values:
- `4`, `7`, `8`
are currently parsed into meaningful outputs.
Other data types are logged but not decoded into a structured output.

Inside `toobur-hr-csv.html`, only:
- `dataType == 3` is parsed/exported (HR CSV)
Other types are ignored.

---
## 5) HR parsing (v3 cmd 0x04, dataType == 3) in `toobur-hr-csv.html`
HR parsing is anchored to JNI callback `7003` described in `docs/callback_7003_hr_json.md`:
- Native layout “before JNI json” contains:
  - `year (u16 LE)`, `month (u8)`, `day (u8)`
  - `startTime (i32 LE)`
  - `dataType (u8)`
  - `silentHR (u8)`
  - 5 threshold/minute pairs (10+3*i, 11+3*i) for `i=0..4`
  - and per-sample items (offset + heart_rateVal), with multiple observed encodings.

### 5.1 Header base offset guess (base 0 vs base 1)
`parseHr7003Header(h)` attempts:
- `base = 0` first
- then `base = 1`

It checks plausibility:
- year must be between `2018..2036`
- month and day must be in valid ranges

When a plausible header is found, it returns:
- `year, month, day, startTime, dataType, silentHR, hrInterval[5]`

### 5.2 Parsing HR samples: how item payloads are interpreted
`parseHrV3(common, headerBytes, dataBytes, fullPayload)` uses:
- `n = common.itemCount` (number of expected items)
- tries a set of decode strategies by comparing `dataBytes.length` to `n`

Decode strategy selection is based on observed patterns:
1. If `n > 0` and `dataBytes.length >= 2 * n`:
   - interpret each sample as 2 bytes:
     - `off = dataBytes[j*2]`  (delta seconds)
     - `bpm = dataBytes[j*2 + 1]`
   - `secondOfDay` accumulates:
     - start from `head.startTime`
     - then add `off` for each sample
   - this mode records:
     - `minuteOffset = off` (raw delta byte)
2. Else if `n > 0` and `dataBytes.length >= 3 * n`:
   - interpret each sample as 3 bytes packed:
     - `minuteOff = parseUint16LE(d, o)`
     - `bpm = d[o+2]`
   - `secondOfDay = head.startTime + minuteOff * 60`
3. Else if `n > 0` and `dataBytes.length >= n`:
   - compute `perItem = Math.floor(dataBytes.length / n)`
   - if `perItem === 1`:
     - interpret as 1 byte BPM per minute index:
       - `bpm = d[i]`
       - `secondOfDay = head.startTime + i * 60`
   - else if `perItem >= 2`:
     - interpret as:
       - `minuteOff = parseUint16LE(d, o)`
       - `bpm = d[o+2]`
       - `secondOfDay = head.startTime + minuteOff * 60`
4. Else if `dataBytes.length > 0` and `n === 0`:
   - treat each byte as raw BPM when in a plausible range:
     - `30..220`

### 5.3 HR CSV export details
`buildCsv(parsed, common, headerBytes)` writes:
- CSV header columns include:
  - `date_ymd,year,month,day,start_time_sec,start_time_unix_sec,data_type,silent_hr`
  - 5 threshold/minute pairs:
    - `thr0,min0,thr1,min1,... thr4,min4`
  - per-sample:
    - `index,minute_offset,second_of_day,sample_time_unix_sec,bpm,parsing_note`

If HR parsing yields zero sample rows:
- it still exports one row with `parsing_note = no_sample_rows`.

---
## 6) Activity parsing (v3 cmd 0x04, dataType == 4) in `confirmed-only.html`
When `common.dataType === 4`, `confirmed-only.html` builds:
- `activityBytes = headerBytes + dataBytes`
and then passes a `DataView` into:
- `parseActivityOutput(activityBuffer, baseOffset)`

### 6.1 Angelfit-style field map used by `parseActivityOutput`
The “Angelfit assumption” field layout map is:
- `DATA_OFFSET = 25`
- `data_activity = {...}`

`parseActivityOutput` interprets each field as either:
- `1-byte` integer
- `2-byte` signed (int16) with little-endian
- `4-byte` unsigned (uint32) with little-endian
- or an array when the map entry uses the `['countKey', offset, itemSize]` form.

For arrays, it reads `item_count` from the previously parsed count key and then:
- repeats `itemSize` bytes per element
- pushes elements based on `itemSize`:
  - `1` -> `getUint8`
  - `2` -> `getInt16`
  - `4` -> `getUint32`

### 6.2 What `confirmed-only.html` actually reports from activity
`logActivityOutput()` logs only a subset:
- `Steps = activity_output.step`
- `Sports = sportLabels[activity_output.type]`
- `kcal = activity_output.calories`
- `BPM` is reported using `avg_hr_value` or `max_hr_value`
- sleep/spo2/relax/blood sugar/hydration/battery are logged as `--`

Additionally, it may generate a TCX export (Garmin TCX) when the activity `version` matches expectations.

---
## 7) Sport summary parsing (v3 cmd 0x04, dataType == 8) in `confirmed-only.html`
When `common.dataType === 8`, `confirmed-only.html` parses:
1. `summary = parseV3SportSummary(headerBytes, dataBytes, common.itemCount)`
2. It also calls:
   - `parseV3SportItems(dataBytes, itemCount)`

### 7.1 Item payload encoding
In `parseV3SportItems(dataBytes, itemCount)`:
- each item size is expected to be exactly `10` bytes
- each item contains:
  - `steps = dataBytes[offset + 0]` (1 byte)
  - `displayCalories = dataBytes[offset + 3]` (1 byte)
  - `distance = dataBytes[offset + 5]` (1 byte)
  - `rawCalories = dataBytes[offset + 7]` (1 byte)
- non-zero items are collected into `nonZeroItems`

Total per-item encoding is therefore:
- itemSize `= 10`
- item i located at `offset = i * 10`

### 7.2 Sport header fields and derived values
In `parseV3SportSummary(headerBytes, dataBytes, itemCount)` (header length must be `>= 20`):
- `version = headerBytes[0]`
- `year = parseUint16LE(headerBytes, 1)`
- `month = headerBytes[3]`
- `day = headerBytes[4]`
- `minuteOffset = parseUint16LE(headerBytes, 5)`
- `intervalMinutes = headerBytes[7]`
- `totalSteps = parseUint32LE(headerBytes, 8)`
- `rawTotalCalories = parseUint32LE(headerBytes, 12)`
- `totalDistance = parseUint32LE(headerBytes, 16)`
- `totalActiveTime = parseUint32LE(headerBytes, 20)` if available
- `headerItemCount = parseUint16LE(headerBytes, 24)` if available
- `headerDisplayCalories = parseUint16LE(headerBytes, 26)` if available

Calorie resolution strategy:
- `totalCalories = headerDisplayCalories || itemTotals.displayCalories || rawTotalCalories`

Coverage computation:
- `coveredUntilMinutes = parseUint16LE(headerBytes, 5) + (itemCount * headerBytes[7])`

### 7.3 What gets logged to the user
`dispatchV3Reply` logs:
- date
- interval minutes and offset
- total steps
- kcal resolved total
- distance
- coveredUntil
- and optionally totalActiveTime

---
## 8) Sleep summary parsing (v3 cmd 0x04, dataType == 7) in `confirmed-only.html`
When `common.dataType === 7`, `confirmed-only.html` parses:
- `summary = parseV3SleepSummary(headerBytes, dataBytes, common.itemCount)`

### 8.1 Sleep header fields (as implemented)
In `parseV3SleepSummary(headerBytes, dataBytes, itemCount)`:
Header length must be at least `>= 16`.

It extracts:
- `version = headerBytes[0]`

Fall asleep time fields:
- `fallAsleepYear = parseUint16LE(headerBytes, 2)`
- `fallAsleepMonth = headerBytes[4]`
- `fallAsleepDay = headerBytes[5]`
- `fallAsleepHour = headerBytes[6]`
- `fallAsleepMin = headerBytes[7]`

Get up time fields:
- `getUpYear = parseUint16LE(headerBytes, 8)`
- `getUpMonth = headerBytes[10]`
- `getUpDay = headerBytes[11]`
- `getUpHour = headerBytes[12]`
- `getUpMin = headerBytes[13]`

Totals:
- `totalMinute = parseUint16LE(headerBytes, 14)`
- `wakeMinute = parseUint16LE(headerBytes, 16)`
- `lightSleepMinute = parseUint16LE(headerBytes, 18)`
- `remSleepMinute = parseUint16LE(headerBytes, 20)`
- `deepSleepMinute = parseUint16LE(headerBytes, 22)`

Optional scoring/goal:
- `sleepScore = headerBytes[26]` (if present)
- `goalSleepData = parseUint16LE(headerBytes, 28)` (if present)

### 8.2 Sleep item encoding (as implemented)
Items are parsed when `dataBytes && n > 0`:
- `n = itemCount`
- `itemSize = 2`
- per item i at `off = i*2`:
  - `stage = dataBytes[off]`
  - `duration = dataBytes[off + 1]`
  - `serialNumber = i`

### 8.3 What gets shown/logged
In `dispatchV3Reply` sleep output formatting uses ONLY header totals:
- It formats `totalMinute` into `HhMm`.
- It then lists:
  - `awake <wakeMinute>m`
  - `light <lightSleepMinute>m`
  - `deep <deepSleepMinute>m`
  - `REM <remSleepMinute>m`

So: per-item `sleepItems[].duration` is currently stored but not used in the summary totals displayed in this UI.

---
## 9) Unverified / known unknowns (from HTML-only view)
1. Sleep item duration unit:
   - `parseV3SleepSummary()` stores `sleepItems[i].duration` as a raw byte without converting units.
   - The code comment says “duration_minutes” for item encoding, but the repo’s GitBook v3 sleep simulator docs (when used) sometimes claim different units for JSON fields.
   - Current UI summary totals come from header fields (`wakeMinute`, `lightSleepMinute`, etc.), not from item durations.
2. Exact semantics of `flag1/flag2/flag3` in the v3 health common header are not decoded in these HTML files.
3. `dataType` values outside `{3,4,7,8}` are not decoded into structured outputs in `confirmed-only.html` and are ignored in `toobur-hr-csv.html`.

---
## 10) Quick reference: “what to implement for a new v3 health data type”
If we later add parsing for `dataType != {3,4,7,8}`:
1. Reuse the shared envelope:
   - `parseV3HealthCommon(payload)`
   - slice `headerBytes` and `dataBytes` using `headSize` and `dataSize`
2. Implement a type-specific decoder:
   - read fixed offsets from `headerBytes`
   - determine item size(s) from `dataBytes.length / itemCount`
3. Add to the dispatcher in the relevant HTML app:
   - `toobur-hr-csv.html` if we want HR-like CSV export
   - `confirmed-only.html` if we want console log decoding

---

## 11) Gadgetbridge TOOBUR: what runs in the app (not the HTML tools)

Code lives under `gadgetbridge/.../service/devices/toobur/`.

### GATT routing (important — do not confuse with GET live data)

| UUID | Role in this fork |
|------|-------------------|
| **`0x0AF6` write** / **`0x0AF7` notify** | **Normal** ID115 pipe: GET/SET (`0x02` / `0x03`), including **GET `0x02` `0xA0` live data** (steps, calories, HR snapshot on card). |
| **`0x0AF1` write** / **`0x0AF2` notify** | **Health / bulk** pipe: VeryFit **v3** frames (`0x33…`) for **health sync** (`0x05` / `0x04`) and **v3 HR mode** (`0x09`) — see `ID115Constants.UUID_CHARACTERISTIC_WRITE_HEALTH`. |

`TooburV3FetchHealthOperation` extends `AbstractID115Operation` with `isHealthOperation() == true`, so it uses **`WRITE_HEALTH` (`0x0AF1`)** and **`NOTIFY_HEALTH` (`0x0AF2`)**, not `0x0AF6`.

### Classes

| Piece | Role |
|-------|------|
| `TooburV3HealthSync` | Builds **v3 `0x05`** (137 B + CRC; seven type+offset records) and **`0x04`** (19 B + CRC). **Reassembly** (`V3ReassemblyBuffer`): strips leading `0x33` per chunk so completed frames start with **`DA AD DA AD…`**. Parses **`0x05`** reply: aggregate **`totalBytes` = u32 LE at **byte offset 11** in that reassembled buffer (first four bytes of v3 payload after `cmd`/`seq`). Dispatches **`0x04`**: HR (`dataType==3`) via `TooburV3HrParser`, sport summary (`dataType==8`) via `parseV3SportSummary`; other types are logged/skipped for persistence. |
| `TooburV3FetchHealthOperation` | **Recorded-data sync** operation (all types in `V3_HEALTH_SYNC_DATA_TYPES`: SpO₂, pressure, HR, activity, swim, sleep, sport): chunked **write on `0x0AF1`**, **notify on `0x0AF2`**. Sequence: send **`0x05`** → on reply, optionally **skip** all **`0x04`** if total unchanged (prefs: `toobur_v3_health_last_total` / sport-probe keys, `toobur_v3_health_fetch_force_full`); else for each type **START (`operate=0`)** then **STOP (`operate=1`)** on **`0x04`**, advancing phases on complete **`0x04`** frames. **DB:** persists **`V3SportSummary`** only (`ID115ActivitySample`); HR and other types are parsed for logs only unless extended later. |
| `TooburSupport.onFetchRecordedData` | Queues **GET `0x02` `0xA0`** on **`0x0AF6`** first, then runs `new TooburV3FetchHealthOperation(this).perform()` (see §13). |

**Not** the same as legacy ID115 **`FetchActivityOperation`** (CMD **`0x08`**): TOOBUR recorded sync uses **v3 `0x05`/`0x04` on `0x0AF1`/`0x0AF2`**.

---

## 12) Scheduling policy: is multi-type v3 sync “expensive”?

Yes. A full run does **one `0x05`** plus **up to seven** type rounds of **`0x04` START + `0x04` STOP**, each potentially multi-packet on BLE, with large replies for HR/sleep/sport. That is **much heavier** than a single **GET live data** (`0x02` `0xA0`).

**Recommended split:**

| Trigger | Suggested behaviour |
|---------|----------------------|
| **User** — device card *Fetch activity data* | Full v3 path (or skip `0x04` if prefs say totals unchanged). User expects completeness. |
| **Background** — Gadgetbridge *auto fetch* (`GBAutoFetchReceiver`, unlock / `USER_PRESENT`) | Respect **minimum minutes** (`auto_fetch_interval_limit`). **30 minutes** is a reasonable default for **full** v3 sync if you want fewer long radio sessions; alternatively rely on **`0x05`-only** or “skip `0x04` when total unchanged” (already in `TooburV3FetchHealthOperation`) to make auto-fetch cheap. |
| **Cheap freshness** — steps / current HR on UI | **GET `0x02` `0xA0`** (live data) only; keep this on **every** fetch and optionally add a **separate** short interval if you implement periodic live polls (not the same as v3 history sync). |

The HTML pages do not enforce this policy; **Gadgetbridge prefs** (`toobur_v3_health_fetch_force_full`, sport offset probe keys) and global **auto fetch** prefs do.

---

## 13) GET live data (`0x02` `0xA0`) vs v3 sync — confirmed behaviour

| Question | Answer |
|----------|--------|
| Is **live data** the same protocol as v3 **`0x04`/`0x05`**? | **No.** Live data is **legacy GET** — write **`0x02` `0xA0`** on **`0x0AF6`**, reply on **`0x0AF7`**. v3 health history sync uses **`0x33`** framing — write on **`0x0AF1`**, reply on **`0x0AF2`**. |
| On **connect** | `TooburSupport.initializeDevice` sends GET **battery**, **device info**, and **live data** once. |
| On **Fetch activity data** (card button) | `onFetchRecordedData` sends **GET live data** first, then starts **`TooburV3FetchHealthOperation`**. |
| On **Gadgetbridge auto fetch** (interval + unlock) | Same `onFetchRecordedData` → **live GET + v3 fetch** for connected devices that support fetching. Interval is **`auto_fetch_interval_limit`** (minutes), not fixed at 30 unless the user sets that. |
| On **swipe refresh** in the device list | **In upstream Gadgetbridge**, “refresh on swipe” is a **preference** (`pref_refresh_on_swipe` / `GBPrefs.refreshOnSwipe()`). **This fork may or may not wire the UI to `onFetchRecordedData`**; if swipe only refreshes the list UI, it does **not** hit the band. **Card “Fetch activity data”** always calls `onFetchRecordedData` in `GBDeviceAdapterv2`. |

**High-frequency live steps/HR** without full v3 history: use **GET `0x02` `0xA0`** on a timer (e.g. every 1–5 minutes when connected) **if** you add that in `TooburSupport`; it is **not** enabled by default in the tree at the time of writing except **on connect** and **whenever sync/fetch runs** (after the `onFetchRecordedData` change above).

