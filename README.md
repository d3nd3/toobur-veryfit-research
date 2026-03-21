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

## Watches using the same protocol

- [Ryze](http://ryzeabove.com.au)
- [IDO Smart / Life](https://www.idoosmart.com)
- [Cove](https://www.coveiot.com)
- bfit Move 2
- Toobur, Runlio, Biggerfive (and other IDO/VeryFit “skins”)

## Features (this repo)

### Gadgetbridge fork (`gadgetbridge/`) — TOOBUR device support

What **works today** (see [`gadgetbridge/README_TOOBUR.md`](gadgetbridge/README_TOOBUR.md) for detail):

- **Connection:** BLE service **0x0AF0**; writes **0x0AF6**, notifications **0x0AF7** and **0x0AF2** (health channel enabled for legacy fetch).
- **Bind (optional):** On each connect, can send VeryFit-style bind start (**`04 01 F1…`**); toggle *Send bind on connect* in device settings.
- **Device info & battery:** GET **0x02 0x01** (firmware / device id on card) and **0x02 0x05** (level %, voltage mV, charging state).
- **Time & basics:** Set time on init + Gadgetbridge sync; wrist side, screen orientation, step goal (ID115 base).
- **Device settings (Toobur screens):** Music on watch, call/notification alert, DND, **raise-to-wake** (9-byte SET **0x28** per captures), one-key SOS, HR mode (SET **0x25**), realtime HR sensor (SET **0x52**), weather switch — each writes the mapped command when changed.
- **Actions:** Find phone, find device, music control, alarms (slots), **reboot** (**`F0 01`**).
- **Activity fetch:** Legacy health transfer (**CMD 0x08** / `FetchActivityOperation`) — **not** full VeryFit v3 health sync (sizes/offsets, multi-type sync) yet.

For **protocol experiments** (many more GET/SET bytes in one place), use **`htmlapp/confirmed-only.html`** in a browser with Web Bluetooth — that panel is **not** the Gadgetbridge app.

### Docs & tooling

- **[`TOOBUR.md`](TOOBUR.md)** — command tables, v3 vs legacy, logcat references, watch-face notes.
- **`packetdumps/logcat/`**, **`bruteforce_results.txt`**, **`scripts/merge_vbus_tx_annotations.py`** — captures and TX labeling.

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
