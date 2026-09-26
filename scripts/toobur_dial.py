#!/usr/bin/env python3
"""List and switch the Toobur A200 watch face (dial) over v3.

v3 `0x0006` returns the installed dial list, v3 `0x0008` activates one by name.
This changes the face with no file upload at all — so it is the cheap way to get
a different dial onto the watch.

Examples:
  python3 scripts/toobur_dial.py                      # list dials
  python3 scripts/toobur_dial.py --set "<name>"       # activate a dial by name
  python3 scripts/toobur_dial.py --silly              # activate a random other dial
  python3 scripts/toobur_dial.py --cycle 5            # walk through 5 dials
"""
from __future__ import annotations

import argparse
import dbus
import dbus.mainloop.glib
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toobur_gatt_dump import (  # noqa: E402
    DEFAULT_MAC,
    DEV_IF,
    PRELUDE_GET,
    connect,
    parse_dial_list,
    send_cmd,
    v3_dial_list,
    v3_dial_set,
)

ADAPTER = "/org/bluez/hci0"
OP_QUERY = 0x00
OP_SET = 0x01


def hx(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def collect(rx: list[bytes], cmd: int) -> list[bytes]:
    """Keep well-formed v3 frames for one command id."""
    out = []
    for f in rx:
        if len(f) >= 14 and f[0] == 0x33 and ((f[8] | (f[9] << 8)) & 0xFFFF) == cmd:
            out.append(f)
    return out


def get_list(bus, path: str, seq: int, wait: float) -> list[dict]:
    rx = send_cmd(bus, path, v3_dial_list(seq), wait=wait)
    frames = collect(rx, 0x0006)
    if not frames:
        print("  no 0x0006 reply", file=sys.stderr)
        return []
    items = parse_dial_list(frames[0]) or []
    if items:
        print(f"  raw payload: {hx(frames[0][12:-2])[:180]}")
    return items


def set_dial(bus, path: str, seq: int, name: str, wait: float,
             op_in: int = OP_SET) -> bool:
    rx = send_cmd(bus, path, v3_dial_set(seq, op_in, name), wait=wait)
    frames = collect(rx, 0x0008)
    if not frames:
        print(f"  set {name!r}: no 0x0008 reply", file=sys.stderr)
        return False
    p = frames[0][12:-2]
    operate, status = (p[0] & 0xFF), (p[1] & 0xFF)
    echo = p[2:].split(b"\x00")[0].decode("ascii", "replace")
    print(f"  set {name!r}: sent_op=0x{op_in:02X} operate_echo={operate} status={status} "
          f"echo={echo!r} -> {'OK' if status == 1 else 'FAILED'}")
    return status == 1


def main() -> int:
    ap = argparse.ArgumentParser(description="List / switch Toobur watch faces")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--set", dest="set_name", help="dial filename to activate")
    ap.add_argument("--silly", action="store_true", help="activate a random non-active dial")
    ap.add_argument("--cycle", type=int, default=0, help="activate N dials in turn")
    ap.add_argument("--query-op", action="store_true", help="send operate=0x00 query instead")
    ap.add_argument(
        "--operate",
        type=lambda s: int(s, 0),
        default=OP_SET,
        help="operate byte (1=set, 0=query); accepts 0x01",
    )
    ap.add_argument("--recheck", action="store_true", help="re-query the list after switching")
    ap.add_argument("--wait", type=float, default=2.5)
    ap.add_argument("--seed", type=int, help="RNG seed for --silly")
    args = ap.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    ok, path = connect(bus, args.mac, ADAPTER)
    if not ok:
        print("connect failed", file=sys.stderr)
        return 2
    print("connected", file=sys.stderr)
    time.sleep(2)
    for name, pkt in PRELUDE_GET:
        print(f"-- prelude {name}", file=sys.stderr)
        send_cmd(bus, path, pkt, wait=1.0)

    print("\n=== dial list (v3 0x0006) ===")
    items = get_list(bus, path, 0x0200, args.wait)
    if not items:
        print("  watch returned no parsable dial list")
        return 1
    for i, d in enumerate(items):
        mark = "  <== ACTIVE" if d["active"] else ""
        print(f"  [{i:>2}] type={d['type']:>3}  {d['name']!r}{mark}")
    active = [d["name"] for d in items if d["active"]]

    if args.query_op:
        print("\n=== dial query (operate=0x00) ===")
        send_cmd(bus, path, v3_dial_set(0x0400, OP_QUERY, active[0] if active else ""),
                 wait=args.wait)
        return 0

    seq = 0x0300
    if args.set_name:
        print(f"\n=== set dial -> {args.set_name!r} (operate=0x{args.operate:02X}) ===")
        rc = set_dial(bus, path, seq, args.set_name, args.wait, args.operate)
        if args.recheck:
            time.sleep(2)
            print("\n=== recheck dial list ===")
            for d in get_list(bus, path, 0x0500, args.wait):
                mark = "  <== ACTIVE" if d["active"] else ""
                print(f"  type={d['type']:>3}  {d['name']!r}{mark}")
        return 0 if rc else 1

    if args.silly or args.cycle:
        rng = random.Random(args.seed)
        others = [d["name"] for d in items if d["name"] not in active] or \
                 [d["name"] for d in items]
        picks = others[: args.cycle] if args.cycle else [rng.choice(others)]
        print(f"\n=== {'cycling' if args.cycle else 'silly pick'} ===")
        okall = True
        for n in picks:
            okall &= set_dial(bus, path, seq, n, args.wait)
            seq += 1
            time.sleep(1.5)
        return 0 if okall else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
