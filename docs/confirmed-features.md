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
