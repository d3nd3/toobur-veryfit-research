#!/usr/bin/env python3
"""Put arbitrary text on the Toobur A200 screen via MSG 0x05 0x03.

The watch renders MSG 0x05 0x03 on screen as a notification, which is the
cheapest "hello world" available without reflashing firmware. Payload layout
mirrors TooburMsgPackets.encodeMessageBody / buildChunkWire:

    body  = type | len(text) | len(phone) | len(title) | phone | title | text
    chunk = 05 03 | totalChunks | idx(1-based) | 16 B slice (zero padded)

Examples:
  python3 scripts/toobur_hello_world.py
  python3 scripts/toobur_hello_world.py --title Hi --body "HELLO WORLD" --type 8
  python3 scripts/toobur_hello_world.py --call            # 05 01 incoming-call form
  python3 scripts/toobur_hello_world.py --body "$(python3 -c 'print("X"*90)')"
"""
from __future__ import annotations

import argparse
import dbus
import dbus.mainloop.glib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toobur_gatt_dump import (  # noqa: E402
    DEFAULT_MAC,
    DEV_IF,
    GATT_CHR,
    NOTIFY_NORMAL,
    OM,
    PRELUDE_GET,
    PROP,
    WRITE_NORMAL,
    connect,
    managed,
    send_cmd,
)

ADAPTER = "/org/bluez/hci0"
CHUNK = 16
MAX_TITLE = 100
MAX_PHONE = 20
MAX_BODY = 100


def trim(s: str, n: int) -> str:
    raw = s.encode()
    if len(raw) <= n:
        return s
    n = max(0, n)
    while n > 0 and (raw[n] & 0xC0) == 0x80:
        n -= 1
    return raw[:n].decode(errors="ignore")


def build_body(msg_type: int, title: str, phone: str, text: str) -> bytes:
    t = trim(title, MAX_TITLE)
    p = trim(phone, MAX_PHONE)
    x = trim(text, MAX_BODY)
    tb, pb, xb = t.encode(), p.encode(), x.encode()
    return bytes([msg_type, len(xb), len(pb), len(tb)]) + pb + tb + xb


def build_call_body(name: str, phone: str) -> bytes:
    n = trim(name, MAX_TITLE)
    p = trim(phone, MAX_PHONE)
    nb, pb = n.encode(), p.encode()
    return bytes([len(pb), len(nb)]) + pb + nb


def chunks(body: bytes):
    total = (len(body) + CHUNK - 1) // CHUNK
    for i in range(total):
        off = i * CHUNK
        raw = body[off : off + CHUNK].ljust(CHUNK, b"\x00")
        yield i + 1, total, bytes([0x05, 0x03, total, i + 1]) + raw


def call_chunks(body: bytes):
    total = (len(body) + CHUNK - 1) // CHUNK
    for i in range(total):
        off = i * CHUNK
        raw = body[off : off + CHUNK].ljust(CHUNK, b"\x00")
        yield i + 1, total, bytes([0x05, 0x01, total, i + 1]) + raw


def hx(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def notify_chars(bus):
    """(write_path, [notify_paths]) for 0x0AF6 + 0x0AF7/0x0AF2."""
    write_p, notes = None, []
    for p, i in managed(bus).items():
        if GATT_CHR not in i:
            continue
        u = str(i[GATT_CHR].get("UUID")).lower()
        if u == WRITE_NORMAL:
            write_p = p
        elif u in (NOTIFY_NORMAL, "00000af2-0000-1000-8000-00805f9b34fb"):
            notes.append(p)
    return write_p, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Show text on the Toobur screen (MSG 05 03)")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--body", default="HELLO WORLD", help="notification body text")
    ap.add_argument("--title", default="", help="sender/title line")
    ap.add_argument("--phone", default="", help="phone number field")
    ap.add_argument("--type", type=int, default=1, help="icon type (1=generic, 8=whatsapp, …)")
    ap.add_argument("--call", action="store_true", help="send as incoming call (05 01) instead")
    ap.add_argument("--repeat", type=int, default=1, help="send the message N times")
    ap.add_argument("--gap", type=float, default=1.2, help="seconds between chunks")
    ap.add_argument("--prelude-only", action="store_true")
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
        send_cmd(bus, path, pkt, wait=1.2)
    if args.prelude_only:
        return 0

    write_p, notes = notify_chars(bus)
    if not write_p:
        print("no 0x0AF6 characteristic", file=sys.stderr)
        return 3

    body = build_call_body(args.title, args.phone) if args.call else build_body(
        args.type, args.title, args.phone, args.body
    )
    plan = call_chunks(body) if args.call else chunks(body)
    plan = list(plan)
    print(f"body ({len(body)} B): {body!r}")
    print(f"chunks: {len(plan)}")

    for _ in range(args.repeat):
        for idx, total, wire in plan:
            rx = send_cmd(bus, path, wire, wait=args.gap)
            acks = [r for r in rx if r and r[0] == 0x05]
            print(f"  chunk {idx}/{total}  TX {hx(wire)}  -> {len(acks)} ack(s)")
        print(f"  sent x{args.repeat}", file=sys.stderr)
        time.sleep(2)

    print("done — check the watch screen", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
