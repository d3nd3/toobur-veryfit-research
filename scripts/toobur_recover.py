#!/usr/bin/env python3
"""Recover a Toobur A200 that is stuck in a boot loop or a wedged transfer session.

Run this the moment the watch advertises again. It escalates, gentlest first:

  1. `F0 01`            reboot        (VBUS 403) — clears a wedged transfer session
  2. `F0 01` again      reboot        — some states need two
  3. `03 27 01`         factory reset (VBUS 115) — LAST RESORT, erases dials + settings

Nothing is sent until the watch is actually found advertising, so this is safe to
leave polling.

Examples:
  python3 scripts/toobur_recover.py --wait 600          # poll up to 10 minutes
  python3 scripts/toobur_recover.py --wait 600 --factory  # go straight to factory reset
  python3 scripts/toobur_recover.py --reboot-only        # never factory reset
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
    OM,
    PRELUDE_GET,
    PROP,
    connect,
    managed,
    send_cmd,
    v3_dial_list,
)

ADAPTER = "/org/bluez/hci0"
FACTORY_DEFAULT = bytes([0x03, 0x27, 0x01])  # SET 0x27, AA = on
REBOOT = bytes([0xF0, 0x01])                 # VBUS 403


def start_scan(bus):
    a = dbus.Interface(bus.get_object("org.bluez", ADAPTER), "org.bluez.Adapter1")
    try:
        a.SetDiscoveryFilter({"Transport": "le"})
    except Exception:
        pass
    try:
        a.StartDiscovery()
    except Exception:
        pass


def is_connected(bus, path):
    try:
        return bool(
            dbus.Interface(bus.get_object("org.bluez", path), PROP).Get(DEV_IF, "Connected")
        )
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Recover a stuck Toobur A200 over BLE")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--wait", type=int, default=300, help="seconds to poll for advertising")
    ap.add_argument("--factory", action="store_true", help="go straight to factory reset")
    ap.add_argument("--reboot-only", action="store_true", help="never send factory reset")
    ap.add_argument("--attempts", type=int, default=2, help="reboot attempts before factory")
    args = ap.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    start_scan(bus)

    print(f"polling for {args.mac} for up to {args.wait}s "
          f"(unplug/replug the charger — it often advertises briefly at boot)...")
    deadline = time.time() + args.wait
    found = False
    while time.time() < deadline:
        for p, ifs in managed(bus).items():
            d = ifs.get(DEV_IF)
            if d and str(d.get("Address", "")).upper() == args.mac.upper():
                found = True
                break
        if found:
            break
        time.sleep(2)

    if not found:
        print("watch never advertised — it needs physical recovery (see docs/custom_firmware.md)")
        return 2
    print("watch is advertising")

    ok, path = connect(bus, args.mac, ADAPTER)
    if not ok:
        print("could not connect")
        return 2
    print("connected")
    time.sleep(2)
    for n, pkt in PRELUDE_GET:
        print(f"-- prelude {n}", file=sys.stderr)
        send_cmd(bus, path, pkt, wait=0.7)

    def show_dials(tag):
        rx = send_cmd(bus, path, v3_dial_list(0x0900), wait=2.5)
        for f in rx:
            if len(f) >= 14 and f[0] == 0x33 and (f[8] | (f[9] << 8)) == 0x0006:
                from toobur_gatt_dump import parse_dial_list

                items = parse_dial_list(f) or []
                names = [d["name"] for d in items]
                print(f"   {tag}: {len(names)} dial(s): {names}")
                return names
        print(f"   {tag}: no dial-list reply")
        return []

    show_dials("before")

    if not args.factory:
        for i in range(1, args.attempts + 1):
            print(f"\n-- reboot {i}/{args.attempts}  F0 01")
            send_cmd(bus, path, REBOOT, wait=3.0)
            time.sleep(8)
            ok2, p2 = connect(bus, args.mac, ADAPTER)
            if ok2:
                path = p2
                time.sleep(2)
                names = show_dials(f"after reboot {i}")
                if names:
                    print("\nwatch is responsive again — dial list came back. Stopping here.")
                    return 0
            else:
                print("   still not reachable; continuing")

    if args.reboot_only:
        print("\n--reboot-only, stopping without factory reset")
        return 1

    print("\n-- FACTORY RESET  03 27 01   (erases dials and settings)")
    send_cmd(bus, path, FACTORY_DEFAULT, wait=3.0)
    time.sleep(12)
    ok3, p3 = connect(bus, args.mac, ADAPTER)
    if ok3:
        path = p3
        time.sleep(3)
        show_dials("after factory reset")
        print("\nfactory reset sent. Leave it on the charger a couple of minutes.")
        return 0
    print("factory reset sent; watch not reachable yet — leave it charging.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
