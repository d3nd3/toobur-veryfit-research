#!/usr/bin/env python3
"""Full GATT tree dump for the TOOBUR over BlueZ D-Bus.

Scans, connects, and walks every service/characteristic/descriptor so
firmware-upload surfaces (Realtek DFU 0x6287, OTA 0xd0ff/0xffd0) are visible.
Those Realtek services usually only appear after the device is put into
OTA mode, so run with --ota to send the OTA_START command first.

Examples:
  python3 scripts/toobur_gatt_dump.py
  python3 scripts/toobur_gatt_dump.py --ota
  python3 scripts/toobur_gatt_dump.py --mac F9:24:12:2E:0C:32 --save
"""
from __future__ import annotations

import argparse
import dbus
import dbus.mainloop.glib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
LIVE_DIR = REPO / "packetdumps" / "live"
DEFAULT_MAC = "F9:24:12:2E:0C:32"

GATT_SVC = "org.bluez.GattService1"
GATT_CHR = "org.bluez.GattCharacteristic1"
GATT_DESC = "org.bluez.GattDescriptor1"
DEV_IF = "org.bluez.Device1"
OM = "org.freedesktop.DBus.ObjectManager"
PROP = "org.freedesktop.DBus.Properties"

# Realtek DFU/OTA UUIDs from com.realsil.sdk.dfu.core.gatt.GattDfuProfile
REALTEK = {
    "00006287-3c17-d293-8e48-14fe2e4da212": "RTK DFU service",
    "00006387-3c17-d293-8e48-14fe2e4da212": "RTK DFU data",
    "00006487-3c17-d293-8e48-14fe2e4da212": "RTK DFU control point",
    "00006587-3c17-d293-8e48-14fe2e4da212": "RTK DFU extend flash",
    "0000d0ff-3c17-d293-8e48-14fe2e4da212": "RTK OTA service",
    "0000ffd0-0000-1000-8000-00805f9b34fb": "RTK OTA service v0",
    "0000ffd1-0000-1000-8000-00805f9b34fb": "RTK OTA control / enter OTA",
    "0000ffd2-0000-1000-8000-00805f9b34fb": "RTK OTA device MAC",
    "0000ffd3-0000-1000-8000-00805f9b34fb": "RTK OTA patch version",
    "0000ffd4-0000-1000-8000-00805f9b34fb": "RTK OTA app version",
    "0000ffd5-0000-1000-8000-00805f9b34fb": "RTK OTA patch ext version",
    "0000ffd8-0000-1000-8000-00805f9b34fb": "RTK OTA test mode",
    "0000fff1-0000-1000-8000-00805f9b34fb": "RTK OTA device info",
    "0000fff2-0000-1000-8000-00805f9b34fb": "RTK OTA image counter",
}

VENDOR_16 = {
    "0af0": "IDO/Toobur main SVC",
    "0af1": "bulk write",
    "0af2": "bulk notify",
    "0af3": "cmd3",
    "0af4": "cmd4",
    "0af5": "cmd5",
    "0af6": "normal write",
    "0af7": "normal notify",
}

SIG = {
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery",
    "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate",
    "00002902-0000-1000-8000-00805f9b34fb": "CCCD",
    "2901-0000-1000-8000-00805f9b34fb": "GATT chr decl",
    "2902-0000-1000-8000-00805f9b34fb": "GATT descriptor",
    "2905-0000-1000-8000-00805f9b34fb": "GATT chr aggregate",
}

# Normal-channel write char we poke for OTA mode entry.
WRITE_NORMAL = "00000af6-0000-1000-8000-00805f9b34fb"
NOTIFY_NORMAL = "00000af7-0000-1000-8000-00805f9b34fb"

# VeryFit app connect prelude (packetdumps/logcat/app_fresh_launch.txt, and
# scripts/toobur_bind_v3.py). The watch ignores most GETs until this runs.
PRELUDE_GET = [
    ("GET device info", bytes([0x02, 0x01])),
    ("GET func table", bytes([0x02, 0x02])),
    ("GET func ex", bytes([0x02, 0x07])),
    ("GET MTU", bytes([0x02, 0xF0])),
    ("v3 func table 1A", bytes.fromhex("33DAADDAAD010B001A0002005FF9")),
]
BIND_START = bytes([0x04, 0x01, 0xF1, 0x01, 0x01, 0x02, 0x02, 0x01, 0x00])


def crc16(data: bytes, off: int, ln: int) -> int:
    """CRC-16/CCITT (poly 0x1021, init 0xFFFF) — the v3 frame checksum."""
    c = 0xFFFF
    for i in range(off, off + ln):
        c ^= data[i] << 8
        for _ in range(8):
            c = (((c << 1) ^ 0x1021) if c & 0x8000 else (c << 1)) & 0xFFFF
    return c


def v3(cmd: int, seq: int, payload: bytes = b"") -> bytes:
    """Build a v3 frame: `33 DA AD DA AD 01 len cmd seq payload crc16`.

    The length field counts every byte after the leading 0x33 and before the
    2-byte CRC, i.e. `len(frame) - 3` — NOT `4 + len(payload)`. Verified against
    TooburV3DialPackets.fillHeader (0x0006 -> 11, 0x0008 -> 42) and against the
    app capture for 0x07/0x1A. Getting this wrong gets silence from the watch.
    """
    inner = 11 + len(payload)
    p = bytearray(
        [
            0x33, 0xDA, 0xAD, 0xDA, 0xAD, 0x01,
            inner & 0xFF, (inner >> 8) & 0xFF,
            cmd & 0xFF, (cmd >> 8) & 0xFF,
            seq & 0xFF, (seq >> 8) & 0xFF,
        ]
    )
    p.extend(payload)
    c = crc16(bytes(p), 1, len(p) - 1)
    p.extend([c & 0xFF, (c >> 8) & 0xFF])
    return bytes(p)


def v3_dial_list(seq: int = 0x0200) -> bytes:
    """v3 0x0006 — GET dial list (TooburV3DialPackets.buildGetListRequest)."""
    return v3(0x0006, seq)


def v3_dial_set(seq: int, operate: int, file_name: str) -> bytes:
    """v3 0x0008 — set active dial by name (operate 0x01 = set)."""
    payload = bytearray(31)
    payload[0] = operate
    name = file_name.encode("ascii", "replace")[:30]
    payload[1 : 1 + len(name)] = name
    return v3(0x0008, seq, bytes(payload))


def parse_dial_list(frame: bytes) -> Optional[List[dict]]:
    """Decode a v3 0x0006 reply into dial entries (see TooburV3DialPackets)."""
    if len(frame) < 14 or frame[0] != 0x33:
        return None
    if (frame[8] | (frame[9] << 8)) != 0x0006:
        return None
    payload = frame[12:-2]
    if len(payload) < 2:
        return None
    count = payload[1] & 0xFF
    items: List[dict] = []
    pos = 6
    for _ in range(count):
        if pos >= len(payload):
            break
        dtype = payload[pos] & 0xFF
        pos += 1
        active = False
        if (
            pos + 5 < len(payload)
            and (payload[pos] & 0xFF) == 0x01
            and 0 < (payload[pos + 1] & 0xFF) < 32
            and payload[pos + 2] == payload[pos + 3] == payload[pos + 4] == 0
        ):
            active = True
            pos += 1
        if pos >= len(payload):
            break
        nlen = payload[pos] & 0xFF
        pos += 4
        if pos + nlen > len(payload):
            break
        name = payload[pos : pos + nlen].decode("ascii", "replace")
        pos += nlen
        items.append({"type": dtype, "active": active, "name": name})
    return items



def label(u: str) -> str:
    u = u.lower()
    if u in REALTEK:
        return f"{u}  <<< {REALTEK[u]}"
    if u in SIG:
        return f"{u}  ({SIG[u]})"
    base = u.replace("-0000-1000-8000-00805f9b34fb", "")
    if len(base) == 4:
        return f"{u}  ({VENDOR_16[base]})" if base in VENDOR_16 else u
    return u


def managed(bus) -> Dict:
    return dbus.Interface(bus.get_object("org.bluez", "/"), OM).GetManagedObjects()


def dev_path(bus, mac: str) -> Optional[str]:
    for p, ifs in managed(bus).items():
        d = ifs.get(DEV_IF)
        if d and str(d.get("Address", "")).upper() == mac.upper():
            return p
    return None


def scan_for(bus, mac: str, adapter: str, seconds: int) -> Optional[str]:
    """Enable discovery and wait for the device to appear in BlueZ's cache."""
    a = dbus.Interface(bus.get_object("org.bluez", adapter), "org.bluez.Adapter1")
    try:
        a.SetDiscoveryFilter({"Transport": "le"})
    except Exception:
        pass
    try:
        a.StartDiscovery()
    except Exception:
        pass
    deadline = time.time() + seconds
    while time.time() < deadline:
        p = dev_path(bus, mac)
        if p:
            return p
        time.sleep(0.5)
    return None


def connect(bus, mac: str, adapter: str, tries: int = 8) -> Tuple[bool, str]:
    """Scan+connect, re-discovering the device object on every attempt.

    The watch advertises in bursts, so BlueZ reaps the device object between
    bursts; a cached path goes stale and raises UnknownObject.
    """
    for i in range(tries):
        path = dev_path(bus, mac)
        if not path:
            path = scan_for(bus, mac, adapter, 20)
        if not path:
            print(f"  attempt {i + 1}/{tries}: not advertising yet", file=sys.stderr)
            time.sleep(1)
            continue
        dev = dbus.Interface(bus.get_object("org.bluez", path), DEV_IF)
        try:
            if bool(dbus.Interface(bus.get_object("org.bluez", path), PROP).Get(DEV_IF, "Connected")):
                return True, path
        except dbus.exceptions.DBusException:
            pass
        try:
            dev.Connect()
        except dbus.exceptions.DBusException as e:
            msg = str(e)
            if "InProgress" not in msg and "AlreadyConnected" not in msg:
                print(f"  connect error: {msg[:80]}", file=sys.stderr)
        deadline = time.time() + 8
        ok = False
        while time.time() < deadline:
            try:
                if bool(
                    dbus.Interface(bus.get_object("org.bluez", path), PROP).Get(DEV_IF, "Connected")
                ):
                    ok = True
                    break
            except dbus.exceptions.DBusException:
                break
            time.sleep(0.25)
        if ok:
            return True, path
        print(f"  attempt {i + 1}/{tries}: connect timed out", file=sys.stderr)
    return False, ""


def send_cmd(bus, path: str, tx: bytes, wait: float = 3.0) -> List[bytes]:
    """Write tx to 0x0AF6 and collect notifications from 0x0AF7 / 0x0AF2."""
    import gi
    from gi.repository import GLib

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    objs = managed(bus)
    write_p = notify_p = None
    for p, i in objs.items():
        if GATT_CHR not in i:
            continue
        u = str(i[GATT_CHR].get("UUID")).lower()
        if u == WRITE_NORMAL:
            write_p = p
        elif u in (NOTIFY_NORMAL, "00000af2-0000-1000-8000-00805f9b34fb"):
            if u == NOTIFY_NORMAL:
                notify_p = p
            else:
                notify_p = notify_p or p
    if not write_p:
        print("  no 0x0AF6 write char", file=sys.stderr)
        return []

    rx: List[bytes] = []
    loop = GLib.MainLoop()
    subs = []
    for p, i in objs.items():
        if GATT_CHR not in i:
            continue
        if str(i[GATT_CHR].get("UUID")).lower() not in (
            NOTIFY_NORMAL,
            "00000af2-0000-1000-8000-00805f9b34fb",
        ):
            continue

        def on_prop(_iface, changed, _invalid):
            v = changed.get("Value")
            if v is not None:
                rx.append(bytes(bytearray(v)))
                print(f"  RX: {' '.join(f'{b:02X}' for b in bytearray(v))}", flush=True)

        o = bus.get_object("org.bluez", p)
        subs.append(dbus.Interface(o, PROP).connect_to_signal("PropertiesChanged", on_prop))
        try:
            dbus.Interface(o, GATT_CHR).StartNotify()
        except Exception:
            pass

    print(f"  TX: {' '.join(f'{b:02X}' for b in tx)}", flush=True)
    try:
        dbus.Interface(bus.get_object("org.bluez", write_p), GATT_CHR).WriteValue(list(tx), {})
    except Exception as e:
        print(f"  write failed: {e}", file=sys.stderr)
    GLib.timeout_add(int(wait * 1000), loop.quit)
    loop.run()
    for p, i in objs.items():
        if GATT_CHR in i and str(i[GATT_CHR].get("UUID")).lower() in (
            NOTIFY_NORMAL,
            "00000af2-0000-1000-8000-00805f9b34fb",
        ):
            try:
                dbus.Interface(bus.get_object("org.bluez", p), GATT_CHR).StopNotify()
            except Exception:
                pass
    return rx


def dump(bus) -> List[str]:
    objs = managed(bus)
    svcs = {p: i[GATT_SVC] for p, i in objs.items() if GATT_SVC in i}
    chr_by_svc: Dict[str, List[Tuple[str, dict]]] = {}
    for p, i in objs.items():
        if GATT_CHR in i:
            chr_by_svc.setdefault(str(i[GATT_CHR].get("Service")), []).append((p, i[GATT_CHR]))
    desc_by_chr: Dict[str, List[Tuple[str, dict]]] = {}
    for p, i in objs.items():
        if GATT_DESC in i:
            desc_by_chr.setdefault(str(i[GATT_DESC].get("Characteristic")), []).append((p, i[GATT_DESC]))

    n = sum(len(v) for v in chr_by_svc.values())
    out = [f"# GATT dump: {n} characteristics in {len(svcs)} services"]
    realtek_seen = []
    for sp, svc in sorted(svcs.items(), key=lambda kv: str(kv[1].get("Primary", ""))):
        out.append("")
        out.append(f"SERVICE {label(str(svc.get('UUID')))}  primary={bool(svc.get('Primary'))} path={sp}")
        for cp, ch in sorted(chr_by_svc.get(sp, []), key=lambda kv: kv[1].get("Handle", 0)):
            cu = str(ch.get("UUID")).lower()
            if cu in REALTEK:
                realtek_seen.append(REALTEK[cu])
            flags = ",".join(str(f) for f in ch.get("Flags", []))
            hint = bytes(bytearray(ch.get("Value", b"")))[:2].hex(" ").upper()
            out.append(f"  CHR {label(str(ch.get('UUID')))} handle={ch.get('Handle')} props={flags} value={hint or '-'}")
            for dp, d in desc_by_chr.get(cp, []):
                out.append(f"    DESC {label(str(d.get('UUID')))} handle={d.get('Handle')}")
    out.append("")
    if realtek_seen:
        out.append("# Realtek DFU/OTA characteristics PRESENT: " + ", ".join(sorted(set(realtek_seen))))
    else:
        out.append("# No Realtek DFU/OTA service visible in normal mode (expected; needs OTA entry)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Dump the Toobur GATT tree over BlueZ D-Bus")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--adapter", default="/org/bluez/hci0")
    ap.add_argument("--scan", type=int, default=30, help="seconds to scan for the device")
    ap.add_argument("--ota", action="store_true", help="send 01 01 (OTA_START) before dumping")
    ap.add_argument(
        "--tx",
        action="append",
        help='raw hex TX on 0x0AF6, repeatable, e.g. --tx "02 01" --tx "02 A7"',
    )
    ap.add_argument("--wait", type=float, default=3.0)
    ap.add_argument("--keep", action="store_true", help="do not disconnect at the end")
    ap.add_argument(
        "--prelude",
        action="store_true",
        help="run the VeryFit connect prelude (GETs) before dumping",
    )
    ap.add_argument(
        "--bind",
        action="store_true",
        help="also send BIND start (04 01 ...); rebinds the watch away from the phone app",
    )
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    path = dev_path(bus, args.mac)
    print(f"connecting to {args.mac} ...", file=sys.stderr)
    ok, path = connect(bus, args.mac, args.adapter)
    if not ok:
        print("connect failed", file=sys.stderr)
        return 2
    print(f"connected {path}", file=sys.stderr)

    # let service discovery settle
    deadline = time.time() + 20
    while time.time() < deadline:
        if any(GATT_SVC in i for i in managed(bus).values()) and any(
            GATT_CHR in i for i in managed(bus).values()
        ):
            break
        time.sleep(0.5)

    if args.ota:
        print("sending OTA_START (01 01) ...", file=sys.stderr)
        send_cmd(bus, path, bytes([0x01, 0x01]), wait=args.wait)
        time.sleep(3)
        print("reconnecting after OTA entry ...", file=sys.stderr)
        try:
            dbus.Interface(bus.get_object("org.bluez", path), DEV_IF).Disconnect()
        except Exception:
            pass
        time.sleep(3)
        ok, path = connect(bus, args.mac, args.adapter, tries=10)
        if not ok:
            print("reconnect failed (device may have rebooted into OTA)", file=sys.stderr)
            return 3

    if args.prelude or args.bind:
        steps = list(PRELUDE_GET) + ([("BIND start", BIND_START)] if args.bind else [])
        for name, pkt in steps:
            print(f"-- prelude: {name}", file=sys.stderr)
            send_cmd(bus, path, pkt, wait=args.wait)

    if args.tx:
        for raw in args.tx:
            tx = bytes(int(x, 16) for x in raw.replace(",", " ").split())
            print(f"-- probe {raw}", file=sys.stderr)
            send_cmd(bus, path, tx, wait=args.wait)

    lines = dump(bus)
    print("\n".join(lines))

    if args.save:
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        p = LIVE_DIR / f"{ts}_gatt-dump{'_ota' if args.ota else ''}.txt"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWrote {p.relative_to(REPO)}", file=sys.stderr)

    if not args.keep:
        try:
            dbus.Interface(bus.get_object("org.bluez", path), DEV_IF).Disconnect()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
