# Gadgetbridge setup (idowatch / TOOBUR)

Instructions used to clone Gadgetbridge into this project, add TOOBUR device support, and build on Kubuntu 25.10. The same build supports **Bangle.js** (via the `banglejs` product flavor) and **TOOBUR** (VeryFit/IDO 0x0AF0) in one APK.

---

## Quick start: compile and put Gadgetbridge on your phone

1. **Prerequisites (once):** JDK 21, Android SDK (`local.properties` or `ANDROID_HOME`), `adb` on PATH. See [§3 JDK](#3-jdk-kubuntu-2510) and [§4 Android SDK](#4-android-sdk).

2. **From the idowatch repo root**, enter the fork and build a **debug APK** (pick one flavor):

   | Flavor | What it is | Compile command |
   |--------|------------|-----------------|
   | **mainline** | Standard Gadgetbridge package id | `./gradlew :app:assembleMainlineDebug` |
   | **banglejs** | Same app + Bangle.js branding / extra permissions (`applicationIdSuffix .banglejs`) — **still includes TOOBUR** and other devices | `./gradlew :app:assembleBanglejsDebug` |

   ```bash
   cd gadgetbridge
   ./gradlew :app:assembleMainlineDebug
   # or
   ./gradlew :app:assembleBanglejsDebug
   ```

3. **Install onto a USB-connected phone** (USB debugging on, device authorized):

   ```bash
   ./gradlew :app:installMainlineDebug
   # or
   ./gradlew :app:installBanglejsDebug
   ```

   This pushes the debug build to the device the same as **Run** from Android Studio.

4. **Or install the APK manually** (e.g. copy over USB/Wi‑Fi, or `adb install`):

   - **Mainline debug APK:**  
     `gadgetbridge/app/build/outputs/apk/mainline/debug/`  
     (filename like `app-mainline-debug.apk` — exact name may vary by Gradle version.)
   - **Bangle.js debug APK:**  
     `gadgetbridge/app/build/outputs/apk/banglejs/debug/`

   ```bash
   adb install -r app/build/outputs/apk/mainline/debug/app-mainline-debug.apk
   # adjust path/filename to match what is on disk; use Tab completion or:
   ls app/build/outputs/apk/mainline/debug/
   ls app/build/outputs/apk/banglejs/debug/
   ```

   **Release** builds (smaller, signed with your keystore if configured):

   ```bash
   ./gradlew :app:assembleMainlineRelease
   ./gradlew :app:assembleBanglejsRelease
   ```

   APKs under `app/build/outputs/apk/<flavor>/release/`.

5. **Side-by-side:** Mainline and Bangle.js builds use **different application IDs**, so you can install **both** debug APKs on one phone if you want.

---

## Run on the phone and read debug logs at the same time

Use **two terminal windows** (or one terminal for `adb logcat` and Android Studio for everything else): one session is for building/installing if needed; the other keeps **`logcat`** streaming while you use the app on the device.

### Application IDs (for filters)

| Flavor | Package name (use in `adb` / Logcat) |
|--------|----------------------------------------|
| **mainline** | `nodomain.freeyourgadget.gadgetbridge` |
| **banglejs** | `com.espruino.gadgetbridge.banglejs` |

### 1) Logcat in a terminal (recommended)

1. Connect the phone over **USB** with **USB debugging** enabled.
2. **Install** the debug APK (see Quick start), then **open Gadgetbridge** on the phone and connect/use the watch so the process is running.
3. In a second terminal, stream logs for **only this app’s process** (PID changes each launch; this picks the current PID):

   **Mainline:**

   ```bash
   adb logcat --pid="$(adb shell pidof -s nodomain.freeyourgadget.gadgetbridge | tr -d '\r')"
   ```

   **Bangle.js flavor:**

   ```bash
   adb logcat --pid="$(adb shell pidof -s com.espruino.gadgetbridge.banglejs | tr -d '\r')"
   ```

   If `pidof` prints nothing, bring Gadgetbridge to the **foreground** on the phone and run the command again.

   If your device’s `pidof` has no `-s` flag, use the first PID from `adb shell pidof nodomain.freeyourgadget.gadgetbridge` manually in `--pid=…`.

4. **Narrow noise** — after you see the stream, you can filter lines (examples):

   ```bash
   adb logcat --pid="$(adb shell pidof -s nodomain.freeyourgadget.gadgetbridge | tr -d '\r')" | grep -iE 'Toobur|ID115|Gatt|BluetoothGatt|ERROR'
   ```

5. **Clear old lines before a repro:**

   ```bash
   adb logcat -c
   ```

6. **Save a session to a file:**

   ```bash
   adb logcat --pid="$(adb shell pidof -s nodomain.freeyourgadget.gadgetbridge | tr -d '\r')" -v time > ~/gadgetbridge-debug.txt
   ```

### 2) Android Studio

1. Open the **`gadgetbridge/`** folder in Android Studio.
2. Choose the **`mainlineDebug`** or **`banglejsDebug`** build variant.
3. Click **Run** (▶) — Studio installs/starts the app and opens the **Logcat** tool window.
4. In Logcat, set the **package** / process filter to the same package name as in the table above so you only see this app’s lines while it runs.

You can keep **Logcat** open and interact with the app on the device; logs update live.

### 3) Wireless debugging (optional)

If the phone uses **wireless debugging** (Android 11+), pair once with `adb pair`, then `adb connect IP:PORT`. After that, the same `adb logcat` commands work without USB.

---

## 0. Compile and install (same as Quick start)

Use the Gradle task names below — the flavor is **`mainline`**, not `main`.

```bash
cd gadgetbridge
./gradlew :app:assembleMainlineDebug
./gradlew :app:installMainlineDebug
```

**Bangle.js flavor:**

```bash
./gradlew :app:assembleBanglejsDebug
./gradlew :app:installBanglejsDebug
```

Connect the phone over USB with **USB debugging** enabled and the RSA prompt accepted before `install*`.

## 1. Clone Gadgetbridge

From the idowatch project root:

```bash
git clone https://github.com/d3nd3/gadgetbridge-veryfit.git gadgetbridge
```

This creates `gadgetbridge/` as our working fork on GitHub.

If you want to keep the original Codeberg repository as upstream:

```bash
cd gadgetbridge
git remote add upstream https://codeberg.org/Freeyourgadget/Gadgetbridge.git
git fetch upstream
```

Changes for this repo are expected in `origin` (the fork), and can be synced with:

```bash
git push origin master
```

---

## 2. TOOBUR device support

TOOBUR-family devices (Toobur, Runlio, Biggerfive, Ksix, IDW, etc.) use the same IDO/Realtek 0x0AF0 GATT protocol as Gadgetbridge’s ID115. We added a dedicated TOOBUR device type that reuses ID115’s protocol and support.

### Changes made

- **`gadgetbridge/app/.../devices/toobur/TooburCoordinator.java`**  
  New coordinator: BLE filter on service 0x0AF0; `supports()` matches device names containing (case-insensitive) Toobur, Runlio, Biggerfive, Ksix, IDW, VeryFit, or Ryze. Uses `ID115Support` and `ID115ActivitySampleDao`.

- **`gadgetbridge/app/.../model/DeviceType.java`**  
  Added `TOOBUR(TooburCoordinator.class)` and import for `TooburCoordinator`. Enum entry placed before `ID115` so TOOBUR-named devices are recognized as TOOBUR first.

- **`gadgetbridge/app/.../res/values/strings.xml`**  
  Added `<string name="devicetype_toobur" translatable="false">TOOBUR</string>`.

No new database entities or GBDaoGenerator changes; TOOBUR reuses ID115 activity samples and support.

---

## 3. JDK (Kubuntu 25.10)

Gadgetbridge’s [setup docs](https://gadgetbridge.org/internals/development/setup-environment/) recommend **OpenJDK 21** for building.

```bash
sudo apt update
sudo apt install openjdk-21-jdk git adb
```

Set `JAVA_HOME` so Gradle finds the JDK (e.g. in `~/.bashrc` or before building):

```bash
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
```

Optional: set as default Java:

```bash
sudo update-alternatives --config java   # pick the java-21 entry
```

---

## 4. Android SDK

The build needs the Android SDK. Either set `ANDROID_HOME` or create a project-local `local.properties` with `sdk.dir`.

**Note:** The Debian/Ubuntu `android-sdk` package does **not** include Google’s `sdkmanager` binary, so `sdkmanager --licenses` will fail with “command not found” unless you install one of the options below.

### Option A: System SDK (apt) + Python sdkmanager

Install the SDK and the Python-based `sdkmanager` (drop-in compatible with Google’s):

```bash
sudo apt update
sudo apt install android-sdk sdkmanager
```

Accept licenses (writes to `/usr/lib/android-sdk/licenses`; sudo required):

```bash
yes | sudo sdkmanager --sdk_root=/usr/lib/android-sdk --licenses
```

Install platform and build-tools (Gadgetbridge uses compileSdk 36 and build-tools 36.0.0):

```bash
sudo sdkmanager --sdk_root=/usr/lib/android-sdk "platform-tools" "platforms;android-36" "build-tools;36.0.0"
```

If `android-36` or `36.0.0` are not available, list and pick the newest:

```bash
sdkmanager --sdk_root=/usr/lib/android-sdk --list
```

You may see a warning like “Observed package id 'build-tools;29.0.3' in inconsistent location .../debian”. It is harmless and can be ignored.

### Option A2: System SDK + Google cmdline-tools (optional)

If you prefer Google’s official sdkmanager instead of the Python one:

```bash
sudo apt install android-sdk google-android-cmdline-tools-19.0-installer
```

Then use the full path to sdkmanager. On Ubuntu the path is often `cmdline-tools/19.0` (not `latest`). Check with:

```bash
find /usr/lib/android-sdk -name sdkmanager
```

Example (path may vary; use the one from `find`):

```bash
yes | sudo /usr/lib/android-sdk/cmdline-tools/19.0/bin/sdkmanager --sdk_root=/usr/lib/android-sdk --licenses
sudo /usr/lib/android-sdk/cmdline-tools/19.0/bin/sdkmanager --sdk_root=/usr/lib/android-sdk "platform-tools" "platforms;android-36" "build-tools;36.0.0"
```

### Option B: Android Studio

Install [Android Studio](https://developer.android.com/studio); the installer will put the SDK in e.g. `~/Android/Sdk`. Use that path for `sdk.dir` below.

### Point the project at the SDK

Create or edit `gadgetbridge/local.properties` (do not commit; it’s machine-specific):

**If using apt SDK (`/usr/lib/android-sdk`):**

```properties
sdk.dir=/usr/lib/android-sdk
```

**If using Android Studio SDK:**

```properties
sdk.dir=/home/YOUR_USERNAME/Android/Sdk
```

Alternatively, set the environment variable and omit `sdk.dir`:

```bash
export ANDROID_HOME=/usr/lib/android-sdk
# or
export ANDROID_HOME=$HOME/Android/Sdk
```

---

## 5. Build

From the Gadgetbridge directory:

```bash
cd gadgetbridge
# Debug APKs (most common):
./gradlew :app:assembleMainlineDebug
./gradlew :app:assembleBanglejsDebug
```

To build **release** APKs (signing config required for publishing; local release builds may use debug keys depending on project setup):

```bash
./gradlew :app:assembleMainlineRelease
./gradlew :app:assembleBanglejsRelease
```

### Bangle.js flavor (includes TOOBUR)

The **banglejs** product flavor changes app identity and permissions (e.g. app name “Bangle.js Gadgetbridge”, `applicationIdSuffix .banglejs`). It does **not** exclude device coordinators — **TOOBUR** and other devices stay in the build.

- **Debug:** `./gradlew :app:assembleBanglejsDebug` → APK under `app/build/outputs/apk/banglejs/debug/`
- **Release:** `./gradlew :app:assembleBanglejsRelease` → `app/build/outputs/apk/banglejs/release/`

Install to a USB-connected device:

```bash
./gradlew :app:installMainlineDebug
./gradlew :app:installBanglejsDebug
```

---

## 6. Troubleshooting

- **“SDK location not found”** — Create `gadgetbridge/local.properties` with `sdk.dir=/usr/lib/android-sdk` (or your SDK path), or set `ANDROID_HOME`.
- **“sdkmanager: command not found”** — The `android-sdk` package does not include sdkmanager. Install the Python wrapper: `sudo apt install sdkmanager` (see §4 Option A).
- **“License for package ... not accepted”** — Run `yes | sudo sdkmanager --sdk_root=/usr/lib/android-sdk --licenses` (or with full path e.g. `/usr/lib/android-sdk/cmdline-tools/19.0/bin/sdkmanager` if using Google cmdline-tools), then install components: `sudo sdkmanager --sdk_root=/usr/lib/android-sdk "build-tools;36.0.0" "platforms;android-36"`.

---

## 7. Reference

- Gadgetbridge setup: https://gadgetbridge.org/internals/development/setup-environment/
- TOOBUR protocol and commands: [TOOBUR.md](TOOBUR.md) in this repo
- Plan used for TOOBUR integration: clone ID115-style 0x0AF0 support, add TooburCoordinator with name-based matching, reuse ID115Support and ID115 activity storage.
