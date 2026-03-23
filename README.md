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
- **Bind / unbind (manual):** VeryFit-style **bind start** (**`04 01 F1…`**) and **unbind** are **only** from device settings → *Send bind* / *Send unbind* (nothing is sent automatically on connect).
- **Device info & battery:** GET **0x02 0x01** (firmware / device id on card) and **0x02 0x05** (level %, voltage mV, charging state).
- **Time & basics:** Set time on init + Gadgetbridge sync; wrist side, screen orientation, step goal (ID115 base).
- **Device settings (Toobur screens):** Music on watch, call/notification alert, DND, **raise-to-wake** (9-byte SET **0x28** per captures), HR mode (SET **0x25** for compatibility) + **VeryFit v3 cmd `0x09`** on **`0x0AF1`** (chunked) for continuous HR / interval — aligned with **`htmlapp/toobur-hr-csv.html`**, weather switch — each writes the mapped command when changed.
- **Actions:** Find phone, find device, music control, alarms (slots), **reboot** (**`F0 01`**), **shutdown** (**`F0 03`**) via Gadgetbridge power off when supported.
- **Activity / health sync:** Pull / auto-fetch runs **`TooburV3FetchHealthOperation`**: **v3 cmd `0x05`** then **`0x04`** for each type (SpO₂ → … → sport); **writes on `0x0AF1`**, replies on **`0x0AF2`**. **Sport summary** (`dataType 0x08`) can be stored as **ID115** samples; other types are parsed/logged as implemented. Legacy **CMD `0x08`** fetch is **not** used for TOOBUR. Wire-level detail: **[`LATEST_SYNC_PARSING.md`](LATEST_SYNC_PARSING.md)** §11–13; packets: **`packetdumps/logcat/sync_example.txt`**. See also [`gadgetbridge/README_TOOBUR.md`](gadgetbridge/README_TOOBUR.md).

For **protocol experiments** (many more GET/SET bytes in one place), use **`htmlapp/confirmed-only.html`** in a browser with Web Bluetooth — that panel is **not** the Gadgetbridge app.

### Docs & tooling

- **[`TOOBUR.md`](TOOBUR.md)** — command tables, v3 vs legacy, logcat references, watch-face notes.
- **[`LATEST_SYNC_PARSING.md`](LATEST_SYNC_PARSING.md)** — v3 health **wire format**, HTML parsers, **Gadgetbridge sync route** (§11–13).
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

Battery and live GETs run **once** from `initializeDevice`; there is **no** built-in periodic battery poll or standalone **`0x05`** timer in the current tree unless you add one.

| Pref (device-specific) | Purpose |
|------------------------|---------|
| `toobur_hr_interval_seconds` | Continuous HR interval for v3 **cmd `0x09`** (**`0x0AF1`**); `255` → smart/dynamic (`0x00FF`). |
| `toobur_v3_health_last_total` | Last aggregate size from v3 **`0x05`** — used to **skip `0x04`** when total has not increased. |
| `toobur_v3_health_fetch_force_full` | If true, do not skip **`0x04`** when total unchanged. |
| `toobur_v3_health_sport_offset_probe` / `toobur_v3_health_sport_offset` / `toobur_v3_health_last_sport_probe_total` | Optional **sport-stream** offset experiments for **`0x05`**. |

Full Gadgetbridge sync route (GATT, classes, live GET vs v3): **[`LATEST_SYNC_PARSING.md`](LATEST_SYNC_PARSING.md)** §11–13.

### Connect / sync flow (high level)

1. **BLE:** Enable **0x0AF7** (normal) and **0x0AF2** (health) notifications. **GET live data** and classic commands use **`0x0AF6`** → **`0x0AF7`**. **v3 health sync** (`0x05` / `0x04`) and **v3 HR mode** (`0x09`) use **`0x0AF1`** → **`0x0AF2`**.
2. **First packets:** Time / wrist / orientation / goal; battery + device info + live data GETs; on **first ever** connect, push all TOOBUR SET prefs + HR mode/interval once. Use *Send bind* only when you need VeryFit-style pairing (not on every connect). **v3 `0x05`/`0x04`** runs when you **fetch activity data** (or auto-fetch), not automatically on every connect in the current code.
3. **While connected:** User-initiated **fetch** / **Gadgetbridge auto-fetch** runs **`onFetchRecordedData`** (GET **`0x02` `0xA0`** + v3 health sync). Interval for auto-fetch is **`auto_fetch_interval_limit`** (minutes), not a fixed 15/30 unless you set that in Gadgetbridge.

For **packet-level** examples, see **`packetdumps/logcat/sync_example.txt`**. Parsing + Gadgetbridge route: **`LATEST_SYNC_PARSING.md`**. Feature status / file map: **`gadgetbridge/README_TOOBUR.md`** and **`TOOBUR.md`**.

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
