#!/usr/bin/env python3
"""Live BLE probe for TOOBUR A200 — capture TX/RX fixtures on demand.

Uses Bleak when installed; falls back to BlueZ D-Bus (same as bind/audit scripts).
Output: packetdumps/live/<timestamp>_<label>.txt (TX : / RX : lines).

Examples:
  python3 scripts/toobur_ble_probe.py --mac F9:24:12:2E:0C:32 battery
  python3 scripts/toobur_ble_probe.py --mac XX:XX --tx "02 10" --label notice
"""
from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
LIVE_DIR = REPO / "packetdumps" / "live"
MAC = "F9:24:12:2E:0C:32"
SVC = "00000af0-0000-1000-8000-00805f9b34fb"
CHARS = {
    "write_normal": "00000af6-0000-1000-8000-00805f9b34fb",
    "notify_normal": "00000af7-0000-1000-8000-00805f9b34fb",
    "write_bulk": "00000af1-0000-1000-8000-00805f9b34fb",
    "notify_bulk": "00000af2-0000-1000-8000-00805f9b34fb",
}
PRESETS = {"battery": "02 05", "notice": "02 10", "dnd": "02 30"}

# BlueZ D-Bus (shared with toobur_bind_v3 / toobur_batch_audit)
GATT_CHR = "org.bluez.GattCharacteristic1"
GATT_SVC = "org.bluez.GattService1"
DEV_IF = "org.bluez.Device1"
OM = "org.freedesktop.DBus.ObjectManager"
PROP = "org.freedesktop.DBus.Properties"


def hx(bs: bytes) -> str:
    return " ".join(f"{b:02X}" for b in bs)


def parse_hex(s: str) -> bytes:
    s = s.replace(" ", "").strip()
    if not s:
        return b""
    if len(s) % 2:
        raise ValueError(f"odd hex length: {s!r}")
    return bytes(int(s[i : i + 2], 16) for i in range(0, len(s), 2))


def preset_tx(name: str) -> bytes:
    if name not in PRESETS:
        raise KeyError(name)
    return parse_hex(PRESETS[name])


def parse_battery(data: bytes) -> Optional[Dict[str, int]]:
    """Match TooburSupport GET 02 05 reply layout (level at byte 6)."""
    if len(data) < 7 or data[0] != 0x02 or data[1] != 0x05:
        return None
    return {
        "type": data[2],
        "voltage_mv": data[3] | (data[4] << 8),
        "status": data[5],
        "level_pct": data[6],
    }


def write_capture(
    out_dir: Path,
    *,
    label: str,
    mac: str,
    tx: bytes,
    rx_list: List[bytes],
    backend: str,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    path = out_dir / f"{ts}_{label}.txt"
    host = socket.gethostname()
    lines = [
        "# Live BLE probe",
        f"# Device: {mac}",
        f"# Host: {host} via {backend} (scripts/toobur_ble_probe.py)",
        f"# Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        f"TX : {hx(tx)}",
    ]
    for rx in rx_list:
        lines.append(f"RX : {hx(rx)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _strip_v3_prefix(data: bytes) -> bytes:
    if data[:5] == bytes([0x33, 0xDA, 0xAD, 0xDA, 0xAD]):
        return data[5:]
    return data


def reply_matches(tx: bytes, rx: bytes) -> bool:
    if len(tx) >= 2 and len(rx) >= 2 and rx[:2] == tx[:2]:
        return True
    inner = _strip_v3_prefix(rx)
    return len(tx) >= 2 and len(inner) >= 2 and inner[:2] == tx[:2]


# --- BlueZ D-Bus transport ---

def _managed(bus) -> Dict:
    import dbus

    return dbus.Interface(bus.get_object("org.bluez", "/"), OM).GetManagedObjects()


def find_device(bus, mac: str) -> Optional[str]:
    for path, ifs in _managed(bus).items():
        d = ifs.get(DEV_IF)
        if d and str(d.get("Address", "")).upper() == mac.upper():
            return path
    return None


def chars_for_service(bus, svc_uuid: str) -> List[Tuple[str, str, List[str]]]:
    out = []
    objs = _managed(bus)
    for path, ifs in objs.items():
        ch = ifs.get(GATT_CHR)
        if not ch:
            continue
        svc_path = str(ch.get("Service", ""))
        if not svc_path:
            continue
        svc = objs.get(svc_path, {}).get(GATT_SVC, {})
        if str(svc.get("UUID", "")).lower() == svc_uuid.lower():
            out.append((path, str(ch["UUID"]), list(ch.get("Flags", []))))
    return out


def run_bluez(mac: str, tx: bytes, wait_s: float = 2.5) -> Tuple[List[bytes], str]:
    import dbus
    import dbus.mainloop.glib
    from gi.repository import GLib

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    dev_path = find_device(bus, mac)
    if not dev_path:
        raise RuntimeError(f"Device {mac} not found — run bluetoothctl scan on")

    dev = dbus.Interface(bus.get_object("org.bluez", dev_path), DEV_IF)
    try:
        dev.Connect()
    except dbus.exceptions.DBusException as e:
        if "AlreadyConnected" not in str(e):
            raise RuntimeError(f"Connect: {e}") from e

    deadline = time.time() + 15
    while time.time() < deadline:
        if dbus.Interface(bus.get_object("org.bluez", dev_path), PROP).Get(DEV_IF, "Connected"):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Timed out waiting for Connected=true")

    paths: Dict[str, str] = {}
    for _ in range(30):
        chars = chars_for_service(bus, SVC)
        for path, uuid, _flags in chars:
            for name, u in CHARS.items():
                if uuid.lower() == u.lower():
                    paths[name] = path
        if len(paths) >= 4:
            break
        time.sleep(0.3)
    missing = [k for k in CHARS if k not in paths]
    if missing:
        raise RuntimeError(f"Missing characteristics: {missing}")

    replies: List[bytes] = []

    def on_notify(_iface, changed, _invalid, _src):
        v = changed.get("Value")
        if v is not None:
            replies.append(bytes(v))

    loop = GLib.MainLoop()
    for key in ("notify_normal", "notify_bulk"):
        p = paths[key]
        dbus.Interface(bus.get_object("org.bluez", p), PROP).connect_to_signal(
            "PropertiesChanged", lambda *a, src=p: on_notify(*a, src=src)
        )
        dbus.Interface(bus.get_object("org.bluez", p), GATT_CHR).StartNotify()

    def write():
        dbus.Interface(bus.get_object("org.bluez", paths["write_normal"]), GATT_CHR).WriteValue(
            list(tx), {}
        )

    GLib.timeout_add(300, lambda: (write(), False))
    GLib.timeout_add(int(wait_s * 1000), loop.quit)
    loop.run()

    for key in ("notify_normal", "notify_bulk"):
        try:
            dbus.Interface(bus.get_object("org.bluez", paths[key]), GATT_CHR).StopNotify()
        except Exception:
            pass
    try:
        dev.Disconnect()
    except Exception:
        pass
    return replies, "BlueZ D-Bus"


# --- Bleak transport ---

async def _run_bleak_async(mac: str, tx: bytes, wait_s: float) -> List[bytes]:
    from bleak import BleakClient

    replies: List[bytes] = []

    def on_notify(_handle, data: bytearray):
        replies.append(bytes(data))

    async with BleakClient(mac, timeout=20.0) as client:
        await client.start_notify(CHARS["notify_normal"], on_notify)
        await client.start_notify(CHARS["notify_bulk"], on_notify)
        await client.write_gatt_char(CHARS["write_normal"], tx, response=True)
        await asyncio.sleep(wait_s)
        await client.stop_notify(CHARS["notify_normal"])
        await client.stop_notify(CHARS["notify_bulk"])
    return replies


def run_bleak(mac: str, tx: bytes, wait_s: float = 2.5) -> Tuple[List[bytes], str]:
    return asyncio.run(_run_bleak_async(mac, tx, wait_s)), "Bleak"


def run_probe(mac: str, tx: bytes, *, backend: str, wait_s: float) -> Tuple[List[bytes], str]:
    if backend == "bleak":
        return run_bleak(mac, tx, wait_s)
    if backend == "bluez":
        return run_bluez(mac, tx, wait_s)
    try:
        import bleak  # noqa: F401
    except ImportError:
        return run_bluez(mac, tx, wait_s)
    return run_bleak(mac, tx, wait_s)


def main() -> int:
    ap = argparse.ArgumentParser(description="TOOBUR A200 live BLE probe")
    ap.add_argument("--mac", default=MAC)
    ap.add_argument(
        "command",
        nargs="?",
        choices=sorted(PRESETS),
        help="preset probe (battery=02 05, notice=02 10, dnd=02 30)",
    )
    ap.add_argument("--tx", help='raw hex TX on 0AF6, e.g. "02 10"')
    ap.add_argument("--label", help="capture filename label (default: command or tx)")
    ap.add_argument("--backend", choices=["auto", "bleak", "bluez"], default="auto")
    ap.add_argument("--wait", type=float, default=2.5, help="seconds to collect notifies")
    ap.add_argument("--no-save", action="store_true", help="skip packetdumps/live write")
    args = ap.parse_args()

    if args.tx:
        tx = parse_hex(args.tx)
        label = args.label or args.command or "tx"
    elif args.command:
        tx = preset_tx(args.command)
        label = args.label or args.command
    else:
        tx = preset_tx("battery")
        label = args.label or "battery"

    print(f"Probe TX: {hx(tx)}  backend={args.backend}  mac={args.mac}")
    try:
        replies, backend_used = run_probe(args.mac, tx, backend=args.backend, wait_s=args.wait)
    except Exception as e:
        print(f"Probe failed: {e}", file=sys.stderr)
        return 1

    for i, rx in enumerate(replies):
        print(f"RX [{i}]: {hx(rx)}")

    if not args.no_save:
        path = write_capture(LIVE_DIR, label=label, mac=args.mac, tx=tx, rx_list=replies, backend=backend_used)
        print(f"Wrote {path.relative_to(REPO)}")

    if label == "battery" or (len(tx) >= 2 and tx[0] == 0x02 and tx[1] == 0x05):
        for rx in replies:
            info = parse_battery(rx)
            if info:
                print(f"Battery: {info['level_pct']}%  {info['voltage_mv']} mV  status={info['status']}")
                break

    ok = any(reply_matches(tx, r) for r in replies)
    if ok:
        print("Reply OK (prefix matches TX).")
        return 0
    print(f"No matching reply ({len(replies)} notify packets).")
    return 2 if replies else 1


if __name__ == "__main__":
    sys.exit(main())
