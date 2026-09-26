#!/usr/bin/env python3
"""BIND + v3 probe — mimics VeryFit connect prelude then health sync."""
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import toobur_ble_probe as probe

MAC = probe.MAC
OUT = ROOT / "packetdumps" / "live" / "2026-06-19_bind-v3.json"
import toobur_v3_sync as v3s

V3_TYPES = v3s.V3_SYNC_ORDER
BYTE14 = v3s.BYTE14
BIND = bytes([0x04, 0x01, 0xF1, 0x01, 0x01, 0x02, 0x02, 0x01, 0x00])
V3_1A = bytes.fromhex("33DAADDAAD010B001A0002005FF9")


def hx(bs: bytes) -> str:
    return " ".join(f"{b:02X}" for b in bs)


def crc16(data: bytes, off: int, ln: int) -> int:
    c = 0xFFFF
    for i in range(off, off + ln):
        c ^= data[i] << 8
        for _ in range(8):
            c = (((c << 1) ^ 0x1021) if c & 0x8000 else (c << 1)) & 0xFFFF
    return c


def v3(cmd: int, seq: int, payload: bytes = b"") -> bytes:
    inner = 4 + len(payload)
    p = bytearray([0x33, 0xDA, 0xAD, 0xDA, 0xAD, 0x01, inner & 0xFF, (inner >> 8) & 0xFF,
                   cmd & 0xFF, (cmd >> 8) & 0xFF, seq & 0xFF, (seq >> 8) & 0xFF])
    p.extend(payload)
    c = crc16(bytes(p), 1, len(p) - 1)
    p.extend([c & 0xFF, (c >> 8) & 0xFF])
    return bytes(p)


def v3_05(seq: int, offsets=None) -> bytes:
    return v3s.build_v3_05(seq, offsets)


def v3_04(seq: int, op: int, dtype: int, save_offset: int = 0) -> bytes:
    return v3s.build_v3_04(seq, op, dtype, save_offset)


def v3_cmd(seq: int, cmd: int, inner: int, tail: bytes) -> bytes:
    head = bytes([0x33, 0xDA, 0xAD, 0xDA, 0xAD, 0x01, inner & 0xFF, (inner >> 8) & 0xFF,
                  cmd & 0xFF, (cmd >> 8) & 0xFF, seq & 0xFF, (seq >> 8) & 0xFF])
    p = bytearray(head + tail)
    c = crc16(bytes(p), 1, len(p) - 1)
    p.extend([c & 0xFF, (c >> 8) & 0xFF])
    return bytes(p)


def v3_0f(seq: int) -> bytes:
    return v3_cmd(seq, 0x0F, 0x0C, bytes([0x00]))


def v3_06(seq: int) -> bytes:
    return v3_cmd(seq, 0x06, 0x0B, b"")


def route(pkt: bytes) -> str:
    return v3s.v3_channel(pkt)


class S:
    def __init__(self):
        self.seq = 0x100
        self.rx: List[Tuple[str, bytes]] = []
        self.results = []
        self.steps: List[Tuple[str, bytes, int]] = []
        self.i = 0
        self.bus = None
        self.dev = None
        self.paths: Dict[str, str] = {}
        self.tags: Dict[str, str] = {}
        self.loop = None

    def ns(self) -> int:
        self.seq += 1
        return self.seq

    def on_rx(self, src, _if, chg, _inv):
        v = chg.get("Value")
        if v is not None:
            b = bytes(v)
            t = self.tags.get(src, "?")
            self.rx.append((t, b))
            print(f"RX [{t}]: {hx(b)[:120]}{'…' if len(b) > 40 else ''}")

    def w(self, ch: str, data: bytes):
        k = "write_normal" if ch == "normal" else "write_bulk"
        tag = "0AF6" if ch == "normal" else "0AF1"
        dbus.Interface(self.bus.get_object("org.bluez", self.paths[k]), probe.GATT_CHR).WriteValue(list(data), {})
        print(f"TX [{tag}]: {hx(data)[:100]}{'…' if len(data) > 50 else ''}")

    def wait_rx(self, pred, ms=3000) -> bool:
        t0 = time.time()
        while (time.time() - t0) * 1000 < ms:
            for _, b in self.rx:
                if pred(b):
                    return True
            time.sleep(0.05)
        return False

    def run(self):
        if self.i >= len(self.steps):
            self.done()
            return False
        name, pkt, wait_ms = self.steps[self.i]
        ch = route(pkt)
        n0 = len(self.rx)
        self.w(ch, pkt)
        GLib.timeout_add(wait_ms, self.check, name, pkt, n0)
        return False

    def check(self, name, pkt, n0):
        window = self.rx[n0:]
        ok = len(window) > 0
        if pkt[:2] == bytes([0x04, 0x01]):
            ok = any(len(b) >= 2 and b[0] == 0x04 and b[1] == 0x01 for _, b in window)
        elif pkt[0] == 0x33 and len(pkt) >= 10:
            cmd = pkt[8] | (pkt[9] << 8)
            ok = any(len(b) >= 10 and b[0] == 0x33 and b[8] == pkt[8] and b[9] == pkt[9] for _, b in window)
            if cmd == 0x04 and len(pkt) > 13:
                dt = pkt[13]
                ok = ok or any(len(b) >= 14 and b[0] == 0x33 and b[13] == dt for _, b in window)
        self.results.append({
            "name": name, "tx": hx(pkt), "channel": route(pkt),
            "status": "ok" if ok else "fail",
            "rx": [hx(b) for t, b in window[:8]],
        })
        print(f"  → {'OK' if ok else 'FAIL'} {name}\n")
        self.i += 1
        self.run()
        return False

    def done(self):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        ok = sum(1 for r in self.results if r["status"] == "ok")
        data = {"mac": MAC, "ok": ok, "fail": len(self.results) - ok, "results": self.results}
        OUT.write_text(json.dumps(data, indent=2))
        print(f"\nWrote {OUT} — OK {ok}/{len(self.results)}")
        try:
            self.dev.Disconnect()
        except Exception:
            pass
        self.loop.quit()

    def go(self, mac: str) -> int:
        subprocess.run(["bluetoothctl", "--timeout", "15", "scan", "on"], capture_output=True)
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        dp = probe.find_device(self.bus, mac)
        if not dp:
            print(f"{mac} not found")
            return 1
        self.dev = dbus.Interface(self.bus.get_object("org.bluez", dp), probe.DEV_IF)
        print(f"Connecting {mac}…")
        try:
            self.dev.Connect()
        except dbus.exceptions.DBusException as e:
            if "AlreadyConnected" not in str(e):
                print(e)
                return 1
        for _ in range(50):
            if dbus.Interface(self.bus.get_object("org.bluez", dp), probe.PROP).Get(probe.DEV_IF, "Connected"):
                break
            time.sleep(0.2)
        chars = []
        for _ in range(30):
            chars = probe.chars_for_service(self.bus, probe.SVC)
            if len(chars) >= 4:
                break
            time.sleep(0.3)
        for path, uuid, _ in chars:
            self.tags[path] = uuid[4:8].upper()
            for n, u in probe.CHARS.items():
                if uuid.lower() == u.lower():
                    self.paths[n] = path
        for nk in ("notify_normal", "notify_bulk"):
            p = self.paths[nk]
            dbus.Interface(self.bus.get_object("org.bluez", p), probe.PROP).connect_to_signal(
                "PropertiesChanged", lambda *a, src=p: self.on_rx(src, *a))
            dbus.Interface(self.bus.get_object("org.bluez", p), probe.GATT_CHR).StartNotify()

        # VeryFit connect prelude (app_fresh_launch.txt)
        prelude = [
            ("GET device info", bytes([0x02, 0x01]), 800),
            ("GET func table", bytes([0x02, 0x02]), 800),
            ("GET func ex", bytes([0x02, 0x07]), 800),
            ("GET MTU", bytes([0x02, 0xF0]), 800),
            ("v3 func table 1A", V3_1A, 1500),
            ("BIND start", BIND, 2000),
        ]
        self.steps.extend(prelude)
        s = self.ns()
        self.steps.append(("v3 health sizes 05", v3_05(s), 3000))
        self.steps.append(("v3 get alarms 0F", v3_0f(self.ns()), 3000))
        self.steps.append(("v3 dial list 06", v3_06(self.ns()), 2000))
        for dtype in V3_TYPES:
            self.steps.append((f"v3 sync {dtype:02X} start", v3_04(self.ns(), 0, dtype), 3000))
            self.steps.append((f"v3 sync {dtype:02X} stop", v3_04(self.ns(), 1, dtype), 1000))

        print(f"Running {len(self.steps)} steps…\n")
        self.loop = GLib.MainLoop()
        GLib.idle_add(self.run)
        self.loop.run()
        return 0 if all(r["status"] == "ok" for r in self.results) else 2


if __name__ == "__main__":
    mac = sys.argv[1] if len(sys.argv) > 1 else MAC
    sys.exit(S().go(mac))
