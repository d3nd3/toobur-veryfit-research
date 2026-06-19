# Confirmed Toobur features

Registry for the [feature confirmation pipeline](../CONTEXT.md#feature-confirmation-pipeline). Each row must match a `@ConfirmedFeature` annotation on a JUnit test; `ConfirmedFeaturesTest` fails on drift.

**Stages:** `tx-confirmed` (TX builder matches capture) → `rx-confirmed` (parser fixture test passes) → `gb-wired` (Gadgetbridge persist + chart).

**Fixtures:** `gadgetbridge/app/src/test/resources/toobur/fixtures/`  
**Extract from logcat:** `scripts/extract_logcat_fixtures.py`  
**Live capture gaps:** [issue 022](../issues/022-bleak-live-probe-tooling/meta.md) (Bleak probe → same fixture format)

| Feature id | Wire | Stage | Test class | Capture source |
|------------|------|-------|------------|----------------|
| `set-notice-03-30` | SET `0x03 0x30` call/notice alert (20 B) | `gb-wired` | `TooburNoticeAlertPacketsTest` | `packetdumps/logcat/app_fresh_launch.txt` |
| `set-dnd-03-29` | SET `0x03 0x29` + GET `0x02 0x30` scheduled DND (14 B) | `gb-wired` | `TooburDndPacketsTest` | `packetdumps/logcat/set_dnd_on.txt`, `set_dnd_off.txt` |
| `set-auto-brightness-03-32` | SET `0x03 0x32` scheduled night brightness (12 B) | `gb-wired` | `TooburAutoBrightnessPacketsTest` | `packetdumps/logcat/set_auto_brightness_on_19pm_to_6am.txt`, `set_auto_brightness_off.txt` |
| `v3-alarms-0e-0f` | v3 GET `0x0F` / SET `0x0E` (10 slots, 353 B) | `gb-wired` | `TooburV3AlarmPacketsTest` | `packetdumps/logcat/get_alarm.txt`, `set_alarms_and_sports.txt` |
| `sleep-sync-v3-07` | v3 cmd `0x04` dataType `0x07` | `gb-wired` | `TooburSleepStoreTest` | `packetdumps/logcat/sync_example.txt` + synthetic sample fixture |
| `hr-sync-v3-03` | v3 cmd `0x04` dataType `0x03` | `gb-wired` | `TooburHrStoreTest` | synthetic JNI-7003 fixture (`hr_v3_type03_sample.rx.hex`) |
| `workout-sync-v3-04` | v3 cmd `0x04` dataType `0x04` | `gb-wired` | `TooburWorkoutStoreTest` | synthetic fixture (`workout_v3_type04_sample.rx.hex`; `sync_example.txt` empty) |
| `swim-sync-v3-06` | v3 cmd `0x04` dataType `0x06` | `gb-wired` | `TooburSwimStoreTest` | `sync_example.txt` empty + synthetic `swim_v3_type06_sample.rx.hex` |
| `device-info-get-02-01` | GET `0x02 0x01` firmware + device id | `gb-wired` | `TooburDeviceInfoPacketsTest` | `packetdumps/live/2026-06-19_get-device-info.txt` |
| `device-info-get-02-04` | GET `0x02 0x04` watch MAC | `gb-wired` | `TooburDeviceInfoPacketsTest` | `packetdumps/logcat/reinstall_app_bind_stripped.txt` |
| `device-info-get-02-a7` | GET `0x02 0xA7` resource pack version | `gb-wired` | `TooburDeviceInfoPacketsTest` | `packetdumps/logcat/get_flashbin_info.txt` |
| `msg-notify-05-03` | MSG `0x05 0x03` notification (16 B chunks, 1-based serial) | `gb-wired` | `TooburMsgPacketsTest` | htmlapp encoding + `SendNotificationOperation` |
| `msg-message-center-05-03` | Message center (same wire as MSG `05 03`) | `gb-wired` | `TooburMsgPacketsTest` | same as `msg-notify-05-03` |
| `msg-call-05-01` | MSG `0x05 0x01` incoming call chunks | `tx-confirmed` | `TooburMsgPacketsTest` | htmlapp encoding (live probe skipped — rings watch) |
| `msg-call-end-05-02` | MSG `0x05 0x02` call dismiss | `tx-confirmed` | `TooburMsgPacketsTest` | `packetdumps/live/2026-06-19_batch-audit.json` |
| `set-music-03-2a` | SET `0x03 0x2A` music on watch (4 B) | `gb-wired` | `TooburMusicWeatherSwitchPacketsTest` | `packetdumps/logcat/set_music_on.txt`, `set_music_off.txt` |
| `set-weather-03-2d` | SET `0x03 0x2D` weather push enable (6 B) | `gb-wired` | `TooburMusicWeatherSwitchPacketsTest` | `packetdumps/logcat/set_push_weather_on.txt`, `set_push_weather_off.txt` |
| `weather-push-0a-01` | CMD `0x0A 0x01` forecast + optional `0A 02` city | `gb-wired` | `TooburWeatherPacketsTest` | `packetdumps/logcat/set_push_weather_on.txt` |
| `set-sport-goal-03-03` | SET `0x03 0x03` sport step goal (17 B) | `gb-wired` | `TooburGoalPacketsTest` | `packetdumps/logcat/app_fresh_launch.txt` |
| `set-sleep-goal-03-04` | SET `0x03 0x04` sleep duration (hour + minute) | `gb-wired` | `TooburGoalPacketsTest` | IDO `protocol_set_sleep_goal`; live ACK `packetdumps/live/2026-06-19_batch-audit.json` |
| `set-calorie-distance-03-43` | SET `0x03 0x43` calorie + distance goals (20 B) | `gb-wired` | `TooburGoalPacketsTest` | `packetdumps/logcat/app_fresh_launch.txt` |
| `ble-notify-07-40` | CMD `0x07 0x40` data-update notify + phone ACK + GET readback | `gb-wired` | `TooburBleEventPacketsTest` | `packetdumps/logcat/set_dnd_on.txt`, `set_hand_gesture_wake_on.txt` |
| `ble-control-music-next-07-01` | CMD `0x07 0x01` cmd1=5 → music next (VBUS 555) | `gb-wired` | `TooburBleEventPacketsTest` | IDO SDK `protocol_exec_ble_control` |
| `ble-control-call-reject-07-01` | CMD `0x07 0x01` cmd1=13 → call reject (VBUS 563) | `gb-wired` | `TooburBleEventPacketsTest` | IDO SDK `protocol_exec_ble_control` |
| `get-func-table-02-02` | GET `0x02 0x02` base func table | `gb-wired` | `TooburConnectSyncPacketsTest` | `packetdumps/live/2026-06-19_batch-audit.json` |
| `get-func-table-ex-02-07` | GET `0x02 0x07` extended func table | `gb-wired` | `TooburConnectSyncPacketsTest` | `packetdumps/live/2026-06-19_batch-audit.json` |
| `v3-func-table-1a` | v3 GET `0x1A` func table extension | `gb-wired` | `TooburConnectSyncPacketsTest` | `packetdumps/live/2026-06-19_bind-v3.json` |
| `set-user-info-03-10` | SET `0x03 0x10` user profile (10 B) | `gb-wired` | `TooburConnectSyncPacketsTest` | `packetdumps/logcat/get_sync_health_v3.txt` |
| `set-units-03-11` | SET `0x03 0x11` units/locale (17 B) | `gb-wired` | `TooburConnectSyncPacketsTest` | `packetdumps/logcat/get_sync_health_v3.txt` |
| `set-conn-param-03-35` | SET `0x03 0x35` conn param steps 01/02 (12 B) | `gb-wired` | `TooburConnectSyncPacketsTest` | `packetdumps/logcat/set_conn_param.txt` |
| `set-misc-e3-03-e3` | SET `0x03 0xE3 0x10 0x02` connect misc | `gb-wired` | `TooburConnectSyncPacketsTest` | `app_fresh_launch.txt` |
| `connect-auto-fetch-v3` | v3 `05`/`04` auto on connect when func table auto-sync bit set | `gb-wired` | `TooburConnectAutoFetchTest` | `packetdumps/live/2026-06-19_bind-v3.json` |
