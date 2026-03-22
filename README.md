# Toobur / VeryFit protocol workspace

A **GadgetBridge** implementation for Toobur and other IDO/angelfit-like smartwatches (Realtek 0x0AF0 protocol), plus related protocol notes and tooling.

The same Toobur watch hardware is sold under multiple names, including **TOOBUR A200** and **TOOBUR BAND 8** (this repo uses both interchangeably).

This project is inspired by the excellent [`xssfox/idowatch`](https://github.com/xssfox/idowatch) work and the associated write-up by sprocketfox: https://sprocketfox.io/xssfox/2025/02/09/ido/.

It also builds on the public [idoosmart/idowatch](https://github.com/idoosmart/idowatch) reference, while the local `gadgetbridge/` folder is the working fork maintained at [d3nd3/gadgetbridge-veryfit](https://github.com/d3nd3/gadgetbridge-veryfit).

## Repository layout

- `gadgetbridge/`  
  Main work-in-progress for TOOBUR device support in the GadgetBridge app.  
  See [`gadgetbridge/README_TOOBUR.md`](gadgetbridge/README_TOOBUR.md) for **feature priority** (bind, health sync, battery, HR, raise-to-wake, etc.).
- `research/repositories/`  
  External reference repos kept as gitlink placeholders here for offline reference.  
  Use `research/repositories/README.md` to fetch them after clone.
- Root docs and scripts  
  - [`TOOBUR.md`](TOOBUR.md) – protocol command table, behavior notes, and device compatibility details.
  - [`gadgetbridge_setup.md`](gadgetbridge_setup.md) – **clone, JDK/SDK, compile Gadgetbridge (mainline or Bangle.js flavor), install the APK**, and **run the app while streaming `adb logcat`** (see *Run on the phone and read debug logs at the same time*).
  - [`GADGETBRIDGE-COLOROS-OPPO.md`](GADGETBRIDGE-COLOROS-OPPO.md) – **optional** ColorOS / OPPO (Android 10, API 29–30) BLE scan + reconnect tuning; **Gadgetbridge → Discovery and pairing** toggle, **default off** (see doc for behavior).

## Watches using the same protocol

- [Ryze](http://ryzeabove.com.au)
- [IDO Smart / Life](https://www.idoosmart.com)
- [Cove](https://www.coveiot.com)
- bfit Move 2
- Toobur, Runlio, Biggerfive (and other IDO/VeryFit “skins”)

## Features (this repo)

### Gadgetbridge fork (`gadgetbridge/`) — TOOBUR device support

On **ColorOS / OPPO phones running Android 10 (API 29–30)**, BLE discovery and reconnect can be flaky. This fork adds an **optional** setting (**OEM BLE reconnect enhancements**) under **Gadgetbridge → Discovery and pairing** — **off by default** so stock behavior is unchanged unless you enable it. Full details: **[`GADGETBRIDGE-COLOROS-OPPO.md`](GADGETBRIDGE-COLOROS-OPPO.md)**.

What **works today** (see [`gadgetbridge/README_TOOBUR.md`](gadgetbridge/README_TOOBUR.md) for detail):

- **Connection:** BLE service **0x0AF0**; writes **0x0AF6**, notifications **0x0AF7** and **0x0AF2** (health notify for v3 sync replies).
- **Bind (optional):** VeryFit-style bind start (**`04 01 F1…`**) is **manual** — device settings → *Send bind start* when you need app pairing (not sent on connect).
- **Device info & battery:** GET **0x02 0x01** (firmware / device id on card) and **0x02 0x05** (level %, voltage mV, charging state).
- **Time & basics:** Set time on init + Gadgetbridge sync; wrist side, screen orientation, step goal (ID115 base).
- **Device settings (Toobur screens):** Music on watch, call/notification alert, DND, **raise-to-wake** (9-byte SET **0x28** per captures), HR mode (SET **0x25**) + **v3 cmd 0x09** continuous HR interval, weather switch — each writes the mapped command when changed.
- **Actions:** Find phone, find device, music control, alarms (slots), **reboot** (**`F0 01`**), **shutdown** (**`F0 03`**) via Gadgetbridge power off when supported.
- **Activity / health sync:** Pull / auto-fetch runs **v3 HR** only (**cmd 0x04** type **0x03**); periodic **v3 cmd 0x05** sizes probes while connected. Legacy ID115 **CMD 0x08** on **0x0AF1** is **not** used (TOOBUR does not respond). **Not** full multi-type v3 persistence yet. See **Sync, intervals & operation** below and [`gadgetbridge/README_TOOBUR.md`](gadgetbridge/README_TOOBUR.md).

For **protocol experiments** (many more GET/SET bytes in one place), use **`htmlapp/confirmed-only.html`** in a browser with Web Bluetooth — that panel is **not** the Gadgetbridge app.

### Docs & tooling

- **[`TOOBUR.md`](TOOBUR.md)** — command tables, v3 vs legacy, logcat references, watch-face notes.
- **`packetdumps/logcat/`**, **`bruteforce_results.txt`**, **`scripts/merge_vbus_tx_annotations.py`** — captures and TX labeling.

## Sync, intervals & operation

Two **independent** mechanisms affect how often data is requested: **Gadgetbridge-wide auto fetch** (activity sync hook) and **TOOBUR support code** (battery, v3 health probe, HR swipe timeout). Manual pull / sync in the UI is **not** limited by the global auto-fetch interval.

### Gadgetbridge (global) — auto fetch

| Setting (prefs key) | Role |
|---------------------|------|
| *Auto fetch activity data* (`auto_fetch_enabled` / `GBPrefs.PREF_AUTO_FETCH_ENABLED`) | Master switch. |
| *Minimum time between fetches* (`auto_fetch_interval_limit` / `GBPrefs.PREF_AUTO_FETCH_INTERVAL_LIMIT`) | Minutes between allowed auto fetches **after** a successful trigger. |

- **Trigger:** `GBAutoFetchReceiver` on **`USER_PRESENT`** (typically unlocking the phone). The in-app summary notes this only works sensibly when a **lock screen** is configured.
- **Debounce:** Ignores further triggers for **2.5 s** after handling one (avoids burst syncs).
- **Effect:** Calls `GBApplication.deviceService().onFetchRecordedData(RecordedDataTypes.TYPE_SYNC)` so each connected device that supports fetching can run its sync path — this is **separate** from TOOBUR’s internal **30 min** v3 probe below.

Code: `gadgetbridge/app/src/main/java/nodomain/freeyourgadget/gadgetbridge/service/receivers/GBAutoFetchReceiver.java`.

### TOOBUR-specific (`TooburSupport` and related)

| Constant / pref | Value | Purpose |
|-----------------|-------|---------|
| `BATTERY_POLL_INTERVAL_MS` | **15 min** | While connected, repeat GET **0x02 0x05** (battery). One read also runs at connect in `initializeDevice`. |
| `V3_HEALTH_SIZES_PROBE_INTERVAL_MS` | **30 min** | While connected, repeat VeryFit v3 **cmd 0x05** (“sizes” / health sync prelude). **First** probe is queued on connect together with NOTIFY setup and live-data GETs. |
| `HR_SWIPE_SYNC_TIMEOUT_MS` | **15 s** | v3 **cmd 0x04** HR pull: if no parsed HR reply, send STOP after this timeout. |
| `toobur_hr_measurement_interval` (`PREF_TOOBUR_HR_INTERVAL`) | User-defined (seconds) | Continuous HR on the band: v3 **cmd 0x09**; `255` → smart/dynamic on the wire (`0x00FF`). |

**Optional v3 sport probing:** `toobur_v3_health_sport_offset_probe` and `toobur_v3_health_last_sport_probe_total` alter how **cmd 0x05** is built when investigating sport offsets (see `TooburSupport`).

### Connect / sync flow (high level)

1. **BLE:** Enable **0x0AF7** (normal) and **0x0AF2** (health) notifications; v3 frames are written on **0x0AF6**; health notify receives v3 replies.
2. **First packets:** Time / wrist / orientation / goal; optional bind; battery + device info + live data GETs; **first v3 cmd 0x05** sizes probe; on **first ever** connect, push all TOOBUR SET prefs + HR mode/interval once.
3. **While connected:** Battery poll every **15 min**; v3 sizes probe every **30 min**; user-initiated sync still goes through Gadgetbridge’s normal fetch path (and is **not** throttled by `auto_fetch_interval_limit`).

For **packet-level** examples (pull vs periodic behavior), see **`packetdumps/logcat/sync_example.txt`**. Feature status and file map: **`gadgetbridge/README_TOOBUR.md`** and **`TOOBUR.md`**.

## Fork and references

The protocol details, BLE layout (`0x0AF6`, `0x0AF7`, `0x0AF1`, `0x0AF2`), command bytes, and many capture traces in this repo are derived from the public IDO ecosystem references.
TOOBUR.md extends that with Toobur/Realtek hardware notes, firmware protocol details (including chunked `MSG 0x05`), watch face upload (`.iwf` / `.iwf.lz`), and notes for integrating angelfit-like devices into GadgetBridge.

See [`gadgetbridge_setup.md`](gadgetbridge_setup.md) — **Quick start** for cloning, compiling **mainline** or **banglejs** flavors, and installing on your phone (`installMainlineDebug` / `installBanglejsDebug`, or `adb install` + APK paths).

## Keeping the GitHub mirror in sync (important)

This repo’s main working tree is `gadgetbridge/`, which is based on the upstream Gadgetbridge repo on Codeberg.

- `upstream` remote: `https://codeberg.org/Freeyourgadget/Gadgetbridge`
- `origin` remote: your GitHub mirror (for example: `https://github.com/d3nd3/gadgetbridge-veryfit`)

To sync your GitHub mirror from Codeberg:

1. Fetch latest from Codeberg:
   ```bash
   git fetch upstream --prune --tags
   ```

2. Pick the sync strategy you want:

   - Exact mirror of Codeberg refs (fastest; overwrites GitHub refs):
     ```bash
     git push --mirror origin
     ```

   - Keep your current GitHub branch history and merge Codeberg in:
     ```bash
     git checkout master
     git merge upstream/master
     git push origin master
     ```

## Other references

- **xssfox/idowatch** ([GitHub](https://github.com/xssfox/idowatch)): minimal “Pair + Get Activity” web app, useful for a non-destructive activity-downloader flow.
- **Angelfit** (protocol reference): https://github.com/orangebrush/angelfit (local copy in `research/repositories/angelfit/`).
- **SDK/API docs** from IDO: https://idoosmart.github.io/Flutter_GitBook/en/ (local copy in `research/repositories/Flutter_GitBook/`).
- [veryFit2googlefit](https://github.com/Durun/veryFit2googleFit/tree/master)
- [IAmFit](https://github.com/mmbatha/IAmFit)
