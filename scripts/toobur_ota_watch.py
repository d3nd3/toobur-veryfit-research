#!/usr/bin/env python3
"""Enter Realtek OTA mode and watch what the watch becomes.

Connects, runs the VeryFit prelude, sends the OTA-start command, then scans
and reports every device that shows up plus the Toobur's GATT tree, so the
post-reboot OTA advertising state can be identified.

Examples:
  python3 scripts/toobur_ota_watch.py
  python3 scripts/toobur_ota_watch.py --cmd "01 02"
  python3 scripts/toobur_ota_watch.py --no-send --watch 45
"""
from __future__ import annotations

import argparse
import dbus
import dbus.mainloop.glib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toobur_gatt_dump import (  # noqa: E402
    BIND_START,
    DEFAULT_MAC,
    DEV_IF,
    GATT_CHR,
    OM,
    PRELUDE_GET,
    PROP,
    REALTEK,
    connect,
    dev_path,
    dump,
    managed,
    send_cmd,
)

REPO = Path(__file__).resolve().parents[1]
LIVE_DIR = REPO / "packetdumps" / "live"
ADAPTER = "/org/bluez/hci0"


def scan_report(bus, seconds: int) -> list[str]:
    a = dbus.Interface(bus.get_object("org.bluez", ADAPTER), "org.bluez.Adapter1")
    try:
        a.SetDiscoveryFilter({"Transport": "le"})
    except Exception:
        pass
    try:
        a.StartDiscovery()
    except Exception:
        pass
    seen: dict[str, dict] = {}
    end = time.time() + seconds
    while time.time() < end:
        for p, ifs in managed(bus).items():
            d = ifs.get(DEV_IF)
            if not d:
                continue
            addr = str(d.get("Address", ""))
            e = seen.setdefault(addr, {"name": "", "rssi": None, "uuids": set(), "mfg": None})
            if d.get("Name"):
                e["name"] = str(d["Name"])
            if d.get("RSSI") is not None:
                e["rssi"] = int(d["RSSI"])
            for u in d.get("UUIDs", []) or []:
                e["uuids"].add(str(u).lower())
            if "ManufacturerData" in d:
                e["mfg"] = d["ManufacturerData"]
        time.sleep(1)
    try:
        a.StopDiscovery()
    except Exception:
        pass

    out = [f"# scan report ({seconds}s) at {datetime.now(timezone.utc):%H:%M:%S} UTC"]
    for addr, e in sorted(seen.items()):
        rtk = sorted(u for u in e["uuids"] if u in REALTEK)
        tag = f"  <<< REALTEK: {', '.join(rtk)}" if rtk else ""
        mfg = ""
        if e["mfg"]:
            mfg = " mfg=" + ",".join(
                f"{k}:{bytes(bytearray(v)).hex(' ').upper()}" for k, v in e["mfg"].items()
            )
        out.append(
            f"{addr}  name={e['name']!r}  rssi={e['rssi']}{mfg}\n"
            f"    uuids={sorted(e['uuids'])}{tag}"
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Enter Toobur OTA mode and report the result")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--cmd", default="01 01", help="OTA command on 0x0AF6 (default 01 01)")
    ap.add_argument("--no-send", action="store_true", help="only scan, do not send anything")
    ap.add_argument("--no-prelude", action="store_true")
    ap.add_argument("--bind", action="store_true")
    ap.add_argument("--watch", type=int, default=45, help="seconds to scan after the command")
    ap.add_argument("--wait", type=float, default=3.0)
    ap.add_argument("--settle", type=int, default=12, help="seconds to wait for the reboot")
    ap.add_argument("--reprobe", action="store_true", help="reconnect and dump GATT afterwards")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    log: list[str] = [
        f"# OTA watch {args.mac} cmd={args.cmd!r} at {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC"
    ]

    if not args.no_send:
        ok, path = connect(bus, args.mac, ADAPTER)
        if not ok:
            print("connect failed", file=sys.stderr)
            return 2
        log.append(f"connected {path}")
        print("connected", file=sys.stderr)
        time.sleep(2)

        if not args.no_prelude:
            for name, pkt in PRELUDE_GET + ([("BIND", BIND_START)] if args.bind else []):
                print(f"-- {name}", file=sys.stderr)
                send_cmd(bus, path, pkt, wait=args.wait)
        if args.bind:
            time.sleep(1)

        cmd = bytes(int(x, 16) for x in args.cmd.replace(",", " ").split())
        print(f"-- OTA command {args.cmd}", file=sys.stderr)
        rx = send_cmd(bus, path, cmd, wait=args.wait)
        log.append(f"TX {args.cmd} -> {len(rx)} notification(s)")
        print(f"-- got {len(rx)} notification(s); waiting {args.settle}s for reboot", file=sys.stderr)
        try:
            dbus.Interface(bus.get_object("org.bluez", path), DEV_IF).Disconnect()
        except Exception:
            pass

    time.sleep(args.settle)
    print(f"-- scanning {args.watch}s", file=sys.stderr)
    log.extend(scan_report(bus, args.watch))

    if args.reprobe:
        print("-- reprobing GATT", file=sys.stderr)
        ok, path = connect(bus, args.mac, ADAPTER)
        if ok:
            time.sleep(3)
            log.append("")
            log.extend(dump(bus))
        else:
            log.append("")
            log.append("# reprobe connect failed")

    text = "\n".join(log)
    print(text)
    if args.save:
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        p = LIVE_DIR / f"{ts}_ota-watch.txt"
        p.write_text(text + "\n", encoding="utf-8")
        print(f"\nWrote {p.relative_to(REPO)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
