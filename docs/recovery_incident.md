# Incident — A200 wedged by a stalled dial upload (2026-09-26)

**Status: OPEN — watch in a boot loop, BLE unreachable, awaiting physical recovery.**

This is the honest record of what went wrong, what I got wrong, what still stands,
and how to get the watch back. Written while the watch is open on the bench.

---

## 1. What happened

1. The `D1` sideload path was working. A full, known-good dial (`witch2`, 53,802 B)
   uploaded cleanly — `D1 03 00` success — appeared in the dial list, and was
   activated with `v3 0x08`. The watch was healthy at that point.
2. A **cosmetic patch** of that same payload (three same-length byte swaps: an ARGB
   colour, the author string, the in-dial name) was then uploaded under a new
   announce name, `silly1.iwf.lz`.
3. That transfer **stalled at 31 of 40 batches** — last write offset 41,540 of the
   expected 53,600. The `D1 03` finish never landed.
4. The transfer session was therefore **never closed**. The watch stayed in
   file-transfer mode: unresponsive to buttons, and re-announcing on every reconnect
   kept re-pinning it in that state rather than letting it time out.
5. The watch is now in a **boot loop**: buzz + HR LED, repeating. Its **BLE stack
   never initialises**, so it never advertises.

## 2. The damage

Almost certainly a **truncated dial file in dial storage**, not a dead board.

The bytes written were a byte-for-byte copy of a *valid* container with three tiny
same-length patches — so what landed is a valid-container *prefix*, not garbage. A
truncated `.iwf` has a TOC pointing past the end of the data, so the dial loader
plausibly crashes at boot, the watchdog fires, and it reboots. That matches the
symptom precisely: it gets far enough to start the UI and the HR sensor, then dies.

`witch2` had already installed and activated cleanly, so the flash and the dial
filesystem were healthy immediately beforehand.

## 3. Recovery attempts, and what they proved

| Attempt | Result |
|---|---|
| `F0 01` reboot (VBUS 403) over BLE | **Impossible** — watch never advertises |
| `03 27 01` factory default (VBUS 115) over BLE | **Impossible** — same |
| Charger recovery | Did not clear it |
| Full battery drain, then recharge | Did **not** clear it — draining the cell does not reset the PMIC or the SoC reset line |
| Long unattended charge | Not yet exhausted |
| Case opened, battery disconnect | **Next step** — a true cold boot |

BLE-based recovery is ruled out permanently in this state. A 23-minute automated
poll plus repeated manual scans found **no** Realtek/CODIX BLE signature at all.
Any recovery that involves talking to the watch needs it to be powered and
radio-alive first.

## 4. Hardware finding — the SoC is CODIX, not Realtek

Close-up of the main QFP reads:

```
CODIX
6952-5
P01 2443
P01M 2617108
```

(exact full part number not yet read — needs a sharper close-up)

**This invalidates the Realtek recovery plan.** `docs/custom_firmware.md` §7.1
previously recommended a Realtek RTL8762 UART/ROM ISP flash with the Realtek MP
Tool, plus an analysis of the RTL8762 eFuse security levels and HCI-Download
password. That was inferred from the vendor app bundling Realtek's
`com.realsil.sdk.dfu` stack. That stack evidently serves **other watch models in
the same app**, not this SoC. **Do not attempt a Realtek ISP flash on this
watch** — wrong vendor, wrong part, real risk of damage.

### What survives the correction

Everything measured on the wire. The IDO application protocol is Realtek-independent
and was reverse-engineered from this device's own captures:

- `v3 0x06` dial list, `v3 0x08` set active dial — both work
- the `D1` file-transfer sequence and its 3-byte `D1 02 00` framing
- the `D1 03` check code being an **additive byte sum** — proven arithmetically
- v3 length field = `len(frame) - 3`
- screen = **120 × 240**
- `.iwf` container header: 38-byte TOC records, `font_head_t` asset headers

None of that depended on the SoC being Realtek.

### Still true about Realtek

The app-side `com.realsil.sdk.dfu` findings stand as **app library** facts (no
signature check, version-based auth, 38-byte TOC struct, `get_file_crc`), and the
`libVeryFitMulti.so` exports (`crc32_z`, `get_file_crc`, `fastlz_*`) are real. They
just do not describe this watch's silicon.

## 4b. SoC positively identified — Goodix GR5515I0NDA (CORRECTS §4)

Full part number: **GR5515I0NDA**, Shenzhen Goodix Technology (汇顶科技).
**CODIX is Goodix's brand** — the chip marking and the part number agree, so §4's
"unknown vendor" is now resolved. ARM Cortex-M4F, BLE 5.1 single-mode.

Supplied with the forum attachments, both official Goodix documents:

- **`GR5515I0ND系列外部Flash选型指导手册` v1.2 (2021-09-06)** — external-flash
  selection guide
- **QSPI pinout diagram** for GR5515I0ND / GR5515I0NDA

### The firmware is on an EXTERNAL SPI NOR flash

| GR5515I0ND/A | Flash |
|---|---|
| GPIO_18 | QSPI_M0_CS_N |
| GPIO_19 | QSPI_M0_IO_3 |
| GPIO_20 | QSPI_M0_CLK |
| GPIO_21 | QSPI_M0_IO_2 |
| GPIO_22 | QSPI_M0_IO_1 |
| GPIO_23 | QSPI_M0_IO_0 |

A plain external SPI NOR, not on-chip flash. Required commands are bog-standard:
reads `0x0B`/`0x03`/`0x3B`/`0xBB`/`0x6B`/`0xEB`, `0x02` page program, `0x20` sector
erase, `0x60` chip erase, `0x9F` JEDEC ID, `0xB9`/`0xAB` power-down, `0x66`/`0x99`
reset. Reference parts include Puya **P25Q128H** (128 Mb) and Winbond **W25Q64JV**
(64 Mb).

### Why this is materially better news

A standard 8-pin SPI NOR is the *best possible* recovery position:

1. **Readable non-destructively** with a ~$3 CH341A USB programmer and an SOP8/OPI
   clip, while still soldered. That tells us whether the firmware is intact or
   whether a sector was left erased by the stalled write — and confirms whether the
   damage is a truncated dial or something worse.
2. **Rewritable in place** if the corruption is confined.
3. **Desolder / reprogram / replace** is a guaranteed fallback, and these parts are
   pennies. No vendor tool, no licence, no account.

Compare with the Realtek theory: wrong vendor, unidentifiable part, no tooling.
This is a commodity part with a dozen programmers and free tools.

### Voltage warning — read before touching anything

The **`A` suffix (GR5515I0NDA) supports both 3.3 V and 1.8 V external flash**;
plain I0ND is 3.3 V only. **Do not assume 3.3 V.** Before putting a 3.3 V programmer
on those QSPI lines, confirm the flash part number and the actual rail. Driving
1.8 V silicon with 3.3 V logic risks damaging it.

## 5. Why the upload stalled — not fully understood

The framing was verified **byte-exact**: rebuilding the unpatched payload
reproduces all 402 captured frames identically and regenerates the capture's
`D1 03 27 6D 4C 00`. So construction was not the fault. Best guess is BLE
saturation — the same stall appeared around frame 370/402 on an earlier verbatim
replay, so it is a transport problem that the retry loop then made fatal by
re-announcing into an already-poisoned session.

## 6. Tooling fixes owed (not yet implemented)

1. **No abort path.** On a stalled data phase the uploader must send a `D1` cancel
   or a correctly-summed finish, never leave the session open. This omission is the
   direct cause of the wedge.
2. **No payload escrow.** Write the payload to a timestamped file before every
   attempt, so a failure is always reproducible offline.
3. **No safe-dial guard.** Refuse to write a new dial unless a known-good dial
   stays active, so a bad file can never be what renders at boot.
4. **Retry loop must back off.** On the first `0x0B`, stop, report, and leave the
   watch alone — do not immediately re-announce.

`scripts/toobur_recover.py` exists for when the watch is radio-alive again; it
escalates `F0 01` ×2 → `03 27 01`, and can poll for advertising.

## 7. Physical recovery plan, in order

1. **Long unattended charge** on the dock (1–2 h). Not yet exhausted.
2. **Reset pinhole** — small hole beside the charging contacts; press with a SIM pin
   5–10 s on the dock. Worth a careful look with a light *before* opening. The case
   is already open, so this is likely moot.
3. **Battery disconnect** ← current step. Unplug the battery connector, wait
   3–5 min, reconnect. A true cold boot; unlike draining the cell this resets the
   PMIC and SoC reset line.
4. **CODIX ISP reflash** — only if 1–3 fail. Needs this SoC's part number and its
   own download protocol, neither identified yet. *Not* the Realtek route.

### Handling cautions

- **Display flex (the orange/copper FPC near the SoC) is the fragile item.** Lift
  straight up, never peel or slide sideways, keep it slack. Its failure is silent
  and total.
- **No metal tools.** Plastic spudger / guitar pick / SIM card only.
- **Never bend or puncture the lithium pouch cell.** Stop if it is swollen.
- Water resistance is already gone regardless.

## 8. If it comes back

Do **not** re-run the dial uploader until items in §6 are fixed. Instead:

- confirm it advertises again (that, not the screen, is the success test)
- list dials with `scripts/toobur_dial.py` — if the active dial is the truncated
  `silly1`, switch to a known-good one
- verify the previously installed `witch2` is intact
- only then re-enable uploads, with a safe-dial guard in place

Nothing in the research is lost. The sideload path was proven working end-to-end
before this, and re-installing a known-good dial takes about two minutes once the
watch is healthy.

## Related

- [`DIAL.md`](../DIAL.md) — the solved sideload path and wire format
- [`iwf_format.md`](iwf_format.md) — container format
- [`custom_firmware.md`](custom_firmware.md) — **§7.1 is corrected by this document**
