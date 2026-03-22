### Single switch (default off)

- Where: Gadgetbridge → Discovery and pairing
- Key: `prefs_oem_ble_reconnect_enhancements` (`GBPrefs.OEM_BLE_RECONNECT_ENHANCEMENTS_*`)
- Default: `false` — users who never enable it get stock behavior (aside from shared plumbing below that stays inert when the pref is off).

---

### What the toggle turns on (when enabled)

1. `BLEScanService`
    
    - API < 31: unfiltered LE scan + software MAC allowlist (hardware `ScanFilter` by address is unreliable).
    - Includes devices in `CONNECTING` in the scan set (not only `WAITING_FOR_SCAN`).
2. `BtLEQueue` – reconnect path
    
    - After unhealthy disconnect, use `WAITING_FOR_SCAN` (scan-then-reconnect) the same way as “Reconnect by BLE scan”, without requiring that global option to be on.
3. `DeviceCommunicationService` – `BLEScanService` lifecycle
    
    - Start `BLEScanService` if OEM _or_ Reconnect by BLE scan is on; stop it when both are off (preference change handler).
4. `BtLEQueue` – `connectGatt` timing
    
    - `getGattConnectDelayMs()` / `onGattConnectDelayScheduled()` on `AbstractBTLEDeviceSupport` (defaults 0 / no-op).
    - `TooburSupport`: when OEM is on, defers `connectGatt` (cold process up to ~10s, else 4.5s); 5s GATT timeout starts only when `connectGatt` actually runs.
5. `DeviceCommunicationService` – `EVENT_DEVICE_FOUND`
    
    - While a deferred TOOBUR `connectGatt` is pending, skip duplicate `connectToDevice` for the same MAC (uses `ServiceDeviceSupport.getDelegate()` + `TooburSupport.isOemDeferredGattConnectPending()`).
6. UI / prefs
    
    - `discovery_pairing_preferences.xml` + strings + restart toast in `DiscoveryPairingPreferenceActivity`.

---

### With the toggle off (other devices / stock path)

- `BLEScanService`: upstream-style filtering / states only.
- Reconnect → `WAITING_FOR_SCAN`: only if global Reconnect by BLE scan is on (unchanged).
- `BLEScanService` start: only if Reconnect by BLE scan is on (OEM does nothing).
- `TooburSupport`: `getGattConnectDelayMs()` → 0 → immediate `connectGatt` like before.
- Duplicate `EVENT_DEVICE_FOUND` guard: not applied (check is behind the OEM pref).

---

### Files touched (for your changelog)

`GBPrefs.java`, `discovery_pairing_preferences.xml`, `strings.xml`, `DiscoveryPairingPreferenceActivity.java`, `BLEScanService.java`, `BtLEQueue.java`, `AbstractBTLEDeviceSupport.java`, `TooburSupport.java`, `ServiceDeviceSupport.java`, `DeviceCommunicationService.java`.

---

Note: `ServiceDeviceSupport.getDelegate()` exists in code for all builds but is only used in the `EVENT_DEVICE_FOUND` path that runs when `getOemBleReconnectEnhancementsEnabled()` is true, so behavior does not depend on it when the toggle is off.