#!/usr/bin/env python3
"""Probe the Toobur A200 `D1` opcode space for a *read* path.

The watch already holds three custom dials (`local_1..3`). If any `D1`
subcommand reads a file back, we get a genuine A200 `.iwf` to analyse — which
is worth more than guessing the container format.

Known: 01=announce, 02=data(TX)+ack(RX), 03=finish, 05=start. This sweeps the
rest, with and without a filename argument, on both the normal and bulk chars.

Examples:
  python3 scripts/toobur_d1_sweep.py
  python3 scripts/toobur_d1_sweep.py --name local_1
"""
from __future__ import annotations

import argparse
import dbus
import dbus.mainloop.glib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toobur_bulk_probe import BULK_WRITE, send_on  # noqa: E402
from toobur_gatt_dump import DEFAULT_MAC, PRELUDE_GET, connect, send_cmd  # noqa: E402

ADAPTER = "/org/bluez/hci0"


def hx(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def summarize(rx: list[bytes]) -> str:
    """Collapse duplicate notifications into unique shapes."""
    seen: list[bytes] = []
    for r in rx:
        if r not in seen:
            seen.append(r)
    if not seen:
        return "(silent)"
    return " | ".join(hx(r)[:88] for r in seen[:3])


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep D1 opcodes looking for a read path")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--name", default="local_1", help="filename to pass as argument")
    ap.add_argument("--wait", type=float, default=1.6)
    args = ap.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    ok, path = connect(bus, args.mac, ADAPTER)
    if not ok:
        print("connect failed", file=sys.stderr)
        return 2
    time.sleep(2)
    for n, pkt in PRELUDE_GET:
        print(f"-- prelude {n}", file=sys.stderr)
        send_cmd(bus, path, pkt, wait=0.9)

    name = args.name.encode()
    forms = {
        "bare": lambda op: bytes([0xD1, op]),
        "name": lambda op: bytes([0xD1, op, 0x00, 0x00, 0x00, 0x02]) + name,
        "name+len": lambda op: bytes([0xD1, op, len(name)]) + name,
    }

    for op in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x0A, 0x0B, 0x10):
        for label, build in forms.items():
            if op in (0x01, 0x03, 0x05) and label != "bare":
                continue  # known-good sequence, don't muddy it
            wire = build(op)
            rx_n = send_cmd(bus, path, wire, wait=args.wait)
            rx_b = send_on(bus, BULK_WRITE, wire, args.wait)
            n_out, b_out = summarize(rx_n), summarize(rx_b)
            if n_out != "(silent)" or b_out != "(silent)":
                print(f"  D1 {op:02X} [{label:>8}] TX {hx(wire)[:40]:<40} "
                      f"normal={n_out}  bulk={b_out}")
        print(f"  -- D1 {op:02X} swept", file=sys.stderr)

    print("\ndone", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
