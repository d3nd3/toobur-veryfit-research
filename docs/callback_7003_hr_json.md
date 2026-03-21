# JNI callback 7003 — HR day JSON (`sub_16DE1C`)

Native code builds JSON and calls `jni_json_data_transfer_callback_data(..., 7003, ...)`.

Struct layout (byte offsets from struct start; BLE HR header often matches through byte 24):

| Offset | Field |
|--------|--------|
| 0 | `year` u16 LE |
| 2 | `month` u8 |
| 3 | `day` u8 |
| 4 | `startTime` s32 LE |
| 8 | `dataType` u8 |
| 9 | `silentHR` u8 |
| 10+3×i | `hrInterval[i].threshold` u8 (i=0..4) |
| 11+3×i | `hrInterval[i].minute` u16 LE |

Items (in memory via pointer at +29; on wire usually contiguous data): pairs **`offset` u8, `heartRateVal` u8** per sample.

`htmlapp/toobur-hr-csv.html` parses v3 type-3 sync using this layout when the header passes year/month/day checks (header base 0 or +1).
