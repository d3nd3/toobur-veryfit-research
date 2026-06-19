# Firmware status & OTA (VeryFit / IDO)

Phase C capability — **read-only status in Gadgetbridge**; **no OTA transfer** is implemented.

## GET `02 48` — firmware status info

| | |
|---|---|
| **Wire** | `02 48` on GATT write `0x0AF6` |
| **VBUS** | `VBUS_EVT_APP_GET_FIRMWARE_STATUS_INFO` (348) |
| **Bruteforce** | VALID on A200 |
| **A200 live** | **No RX** — `packetdumps/live/2026-06-19_batch-audit.json` |

Gadgetbridge queues GET `02 48` on connect (after MAC / flash GETs) and from **Developer → Query firmware status**. When a reply arrives, the device card shows a **Firmware OTA** row via `TooburFirmwareStatusPackets`.

### Reply layout — `needs-capture`

No A200 RX exists in this repo. Parser fields follow a **provisional** IDO-style layout (status + 3-byte version triple + update flag + optional target triple). Confirm with a live probe on a watch that returns `02 48` (VeryFit OTA-capable SKU) or a logcat capture during “check for updates” in the official app.

Fixture: `gadgetbridge/app/src/test/resources/toobur/fixtures/firmware_status_synthetic.rx.hex` (synthetic only).

## OTA command pipe — documented, not shipped

| Step | Wire | VBUS | Notes |
|------|------|------|-------|
| Enter upgrade mode | `01 01` | 400 OTA_START | Bruteforce VALID; reply `err_flag`: 0=OK, 1=low battery, 2=unsupported, 3=bad param (IDO GitBook) |
| Direct start (ignore battery) | `01 02` | 401 | Not probed on A200 |
| OTA auth (Realtek) | `01 03` | 407 | VBUS only |
| Firmware bytes | bulk on `0x0AF1` | — | Same chunked pipe as v3 health / watch faces |

**Policy:** Any future OTA implementation must require **explicit user confirmation** per flash — no silent or connect-time OTA.

### Blockers for full OTA in GB

1. GET `02 48` RX layout unconfirmed on reference A200.
2. No `.zip` / image format mapping for Toobur A200 in repo (IDO cloud DFU is server-side).
3. `01 02` / `01 03` + bulk ACK sequence needs a full VeryFit OTA btsnoop capture.
4. High brick risk — gate behind Developer + confirm dialog + battery check.

## Related

- Device card baseline: issue 010 (GET `02 01` / `04` / `A7`).
- Watch faces bulk path: issue 019 (same `0x0AF1` pipe).
- Live probe: issue 022 / `scripts/toobur_batch_audit.py` (GET `48` entry).
