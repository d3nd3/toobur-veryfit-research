# Goodix GR5515 references

Extracted from vendor documentation supplied by the user on 2026-09-26, from
`bbs.16rd.com` thread `tid=601676`. Upstream is Shenzhen Goodix Technology
(深圳市汇顶科技股份有限公司), <https://www.goodix.com>.

Why this matters: the Toobur A200's SoC is a **Goodix GR5515I0NDA** (chip brand
marking `CODIX`, which is Goodix's brand), and its firmware lives in an
**external SPI NOR flash** rather than on-chip. That is what makes the watch
recoverable with commodity tools.

## Files

| File | What it is |
|---|---|
| `GR5515I0ND_external_flash_guide_v1.2_extracted.txt` | Text extract of 《GR5515I0ND系列外部Flash选型指导手册》v1.2, 2021-09-06 |
| `GR5515_qspi_pinout.jpg` | Official QSPI pin assignment diagram, GR5515I0ND / GR5515I0NDA |

Binaries are not committed here; the text extract and diagram are kept because the
facts below are what the repo actually needs.

## Key facts

**QSPI interface to the external flash:**

| GR5515I0ND/A | Flash |
|---|---|
| GPIO_18 | QSPI_M0_CS_N |
| GPIO_19 | QSPI_M0_IO_3 |
| GPIO_20 | QSPI_M0_CLK |
| GPIO_21 | QSPI_M0_IO_2 |
| GPIO_22 | QSPI_M0_IO_1 |
| GPIO_23 | QSPI_M0_IO_0 |

**Required SPI NOR commands** (a conforming flash must support at least these):

| Function | Code |
|---|---|
| Read Array (fast) | `0x0B` |
| Read Array (low power) | `0x03` |
| Read Dual Output | `0x3B` |
| Read 2x I/O | `0xBB` |
| Read Quad Output | `0x6B` |
| Read 4x I/O | `0xEB` |
| Sector Erase (4 KiB) | `0x20` |
| Chip Erase | `0x60` |
| Page Program | `0x02` |
| Program/Erase Suspend / Resume | `0x75` / `0x7A` |
| Read Status Register 1 / 2 | `0x05` / `0x35` |
| Write Status Register | `0x01` |
| Reset Enable / Reset | `0x66` / `0x99` |
| Read Manufacturer/Device ID (JEDEC) | `0x9F` |
| Deep Power-down / Release | `0xB9` / `0xAB` |

**Reference flash parts** (guide §4): Puya `P25Q128H` (128 Mb, 2.30–3.60 V),
Winbond `W25Q64JV` (64 Mb, 2.70–3.60 V), and others listed in the extract.

## ⚠️ Voltage caveat

`GR5515I0NDA` (the `A` suffix) supports **both** 3.3 V and 1.8 V external flash.
`GR5515I0ND` (no `A`) is 3.3 V only. **Confirm the flash part marking and the actual
supply rail before driving 3.3 V logic onto the QSPI lines** — 1.8 V silicon does not
tolerate it.

## Also in the guide

§5 covers practical notes worth knowing before a rework attempt: `tRES1` parameter
configuration, enabling SPI 4-wire mode, and implementing non-standard flash commands.

## Related

- [`../../docs/recovery_incident.md`](../../docs/recovery_incident.md) §4b — why this
  identification changed the recovery plan
- [`../../docs/custom_firmware.md`](../../docs/custom_firmware.md) §7 — corrected firmware route
