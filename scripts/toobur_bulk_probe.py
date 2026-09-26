#!/usr/bin/env python3
"""Probe the Toobur A200 bulk file-transfer channel (`D1`) and v3 device metadata.

Three questions, in order of value:
  1. does v3 `0x07` answer, and what is the real screen geometry?
  2. does `D1 01` (announce filename) get an ACK on the bulk channel?
  3. does `D1 05` (start) get an ACK, i.e. is the file channel writable at all?

Wire shapes are taken from packetdumps/logcat/ui_watch_face_write_json.txt
(the official app's own watch-face upload).

Examples:
  python3 scripts/toobur_bulk_probe.py
  python3 scripts/toobur_bulk_probe.py --name HELLO.iwf.lz
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
    PRELUDE_GET,
    WRITE_NORMAL,
    connect,
    crc16,
    managed,
    send_cmd,
    v3,
)

BULK_WRITE = "00000af1-0000-1000-8000-00805f9b34fb"
BULK_NOTIFY = "00000af2-0000-1000-8000-00805f9b34fb"
NORMAL_NOTIFY = "00000af7-0000-1000-8000-00805f9b34fb"
ADAPTER = "/org/bluez/hci0"


def hx(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def chars(bus):
    w = b = None
    for p, i in managed(bus).items():
        if GATT_CHR not in i:
            continue
        u = str(i[GATT_CHR].get("UUID")).lower()
        if u == BULK_WRITE:
            w = p
        elif u == BULK_NOTIFY:
            b = p
    return w, b


def send_on(bus, path: str, tx: bytes, wait: float):
    """Write tx on a specific characteristic and collect its notifications."""
    import gi
    from gi.repository import GLib

    objs = managed(bus)
    target = None
    listen = []
    for p, i in objs.items():
        if GATT_CHR not in i:
            continue
        u = str(i[GATT_CHR].get("UUID")).lower()
        if u == path:
            target = p
        if u in (NORMAL_NOTIFY, BULK_NOTIFY):
            listen.append(p)
    if not target:
        return []

    rx: list[bytes] = []

    def on_prop(_iface, changed, _inv):
        v = changed.get("Value")
        if v is not None:
            rx.append(bytes(bytearray(v)))

    loop = GLib.MainLoop()
    subs = []
    for p in listen:
        o = bus.get_object("org.bluez", p)
        subs.append(dbus.Interface(o, "org.freedesktop.DBus.Properties").connect_to_signal(
            "PropertiesChanged", on_prop))
        try:
            dbus.Interface(o, GATT_CHR).StartNotify()
        except Exception:
            pass
    try:
        dbus.Interface(bus.get_object("org.bluez", target), GATT_CHR).WriteValue(list(tx), {})
    except Exception as e:
        print(f"    write failed: {e}", file=sys.stderr)
    GLib.timeout_add(int(wait * 1000), loop.quit)
    loop.run()
    for p in listen:
        try:
            dbus.Interface(bus.get_object("org.bluez", p), GATT_CHR).StopNotify()
        except Exception:
            pass
    return rx


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe Toobur bulk D1 file channel")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--name", default="hello.iwf.lz")
    ap.add_argument("--wait", type=float, default=2.5)
    args = ap.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    ok, path = connect(bus, args.mac, ADAPTER)
    if not ok:
        print("connect failed", file=sys.stderr)
        return 2
    time.sleep(2)
    for name, pkt in PRELUDE_GET:
        print(f"-- prelude {name}")
        send_cmd(bus, path, pkt, wait=1.2)

    print("\n=== 1. v3 0x07 device metadata (screen geometry) ===")
    for rx in send_cmd(bus, path, v3(0x07, 0x0150), wait=args.wait):
        if rx[:5] == bytes([0x33, 0xDA, 0xAD, 0xDA, 0xAD]):
            payload = rx[13:-2]
            print(f"  RX {hx(rx)}")
            print(f"  payload {hx(payload)}")
            txt = bytes(payload)
            if b"Band" in txt or b"IDW" in txt or b"A2" in txt:
                print(f"  ascii  {txt!r}")
            if len(payload) >= 18:
                w = payload[8] | (payload[9] << 8)
                h = payload[10] | (payload[11] << 8)
                print(f"  >>> candidate geometry: {w} x {h}")

    wpath, bpath = chars(bus)
    print(f"\nbulk write char: {wpath}")

    print("\n=== 2. D1 01 announce (normal channel, as the app does) ===")
    name = args.name.encode()
    announce = bytes([0xD1, 0x01, 0xFF, 0x2A, 0xD2, 0x00, 0x00, 0x02]) + name
    print(f"  TX {hx(announce)}  ({len(announce)} B, name={args.name!r})")
    for rx in send_cmd(bus, path, announce, wait=args.wait):
        print(f"  RX {hx(rx)}")

    print("\n=== 3. D1 01 on the BULK channel ===")
    for rx in send_on(bus, BULK_WRITE, announce, args.wait):
        print(f"  RX {hx(rx)}")

    print("\n=== 4. D1 05 start (normal) ===")
    d105 = bytes([0xD1, 0x05, 0x0A])
    print(f"  TX {hx(d105)}")
    for rx in send_cmd(bus, path, d105, wait=args.wait):
        print(f"  RX {hx(rx)}")

    print("\n=== 5. D1 05 start (bulk) ===")
    for rx in send_on(bus, BULK_WRITE, d105, args.wait):
        print(f"  RX {hx(rx)}")

    print("\n=== 6. D1 02 data chunks ===")
    # Framing derived from the app capture: the watch ACKs a write offset with a
    # stride of 1340 = 10 x 134, so each MTU-bound frame is `D1 02 00` + 134 file
    # bytes (137 total). A 135-byte payload desyncs the stream (watch replies 0x09).
    chunk_payload = 134
    body = bytes((i * 7 + 3) & 0xFF for i in range(chunk_payload * 12))
    n = 0
    for off in range(0, len(body), chunk_payload):
        n += 1
        wire = bytes([0xD1, 0x02, 0x00]) + body[off : off + chunk_payload]
        assert len(wire) == 137, len(wire)
        rx = send_cmd(bus, path, wire, wait=1.2)
        interesting = [r for r in rx if r[:2] == b"\xD1\x02"]
        acks = [f"st={r[2]:02X}" + (f" idx={r[5]:02X} off={int.from_bytes(r[7:11], 'little')}" if len(r) >= 11 else "")
                for r in interesting]
        print(f"  chunk {n:>2}: TX 137 B -> {len(interesting)} ack(s) {' '.join(acks)}")

    print("\n=== 7. D1 03 finish ===")
    d103 = bytes([0xD1, 0x03])
    print(f"  TX {hx(d103)}")
    for rx in send_cmd(bus, path, d103, wait=args.wait):
        print(f"  RX {hx(rx)}")

    print("\n=== 8. does the file show up? v3 0x06 dial list ===")
    for rx in send_cmd(bus, path, v3(0x06, 0x0200), wait=args.wait):
        if rx[:5] == bytes([0x33, 0xDA, 0xAD, 0xDA, 0xAD]):
            print(f"  RX {hx(rx)[:200]}")
            tail = rx[13:-2]
            txt = bytes(tail)
            printable = "".join(chr(c) if 32 <= c < 127 else "." for c in txt)
            print(f"  ascii: {printable}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
