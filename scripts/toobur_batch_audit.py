#!/usr/bin/env python3
"""Fast live audit of TOOBUR A200 protocol features — one BLE session."""
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import toobur_ble_probe as probe

MAC = probe.MAC
OUT = ROOT / "packetdumps" / "live" / "2026-06-19_batch-audit.json"
import toobur_v3_sync as v3s

V3_TYPES = v3s.V3_SYNC_ORDER
BYTE14 = v3s.BYTE14


def hx(bs: bytes) -> str:
    return " ".join(f"{b:02X}" for b in bs)


def parse_hex(s: str) -> bytes:
    s = s.replace(" ", "")
    return bytes(int(s[i : i + 2], 16) for i in range(0, len(s), 2))


def crc16_ccitt_false(data: bytes, offset: int, length: int) -> int:
    crc = 0xFFFF
    for i in range(offset, offset + length):
        crc ^= data[i] << 8
        for _ in range(8):
            crc = (((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)) & 0xFFFF
    return crc


def finalize_crc(packet: bytearray) -> None:
    c = crc16_ccitt_false(bytes(packet), 1, len(packet) - 3)
    packet[-2] = c & 0xFF
    packet[-1] = (c >> 8) & 0xFF


def v3_packet(cmd: int, seq: int, payload: bytes = b"") -> bytes:
    inner = 4 + len(payload)
    p = bytearray(
        [0x33, 0xDA, 0xAD, 0xDA, 0xAD, 0x01, inner & 0xFF, (inner >> 8) & 0xFF,
         cmd & 0xFF, (cmd >> 8) & 0xFF, seq & 0xFF, (seq >> 8) & 0xFF]
    )
    p.extend(payload)
    finalize_crc(p)
    return bytes(p)


def build_v3_05(seq: int, offsets=None) -> bytes:
    return v3s.build_v3_05(seq, offsets)


def build_v3_04(seq: int, operate: int, dtype: int, save_offset: int = 0) -> bytes:
    return v3s.build_v3_04(seq, operate, dtype, save_offset)


@dataclass
class Step:
    name: str
    wire: str
    tx: bytes
    channel: str  # normal | bulk
    expect: str  # classic | v3cmd:NN | ack:03xx | any
    wait_ms: int = 700


@dataclass
class Result:
    name: str
    wire: str
    status: str  # ok | fail | skip | user
    tx: str = ""
    rx: List[str] = field(default_factory=list)
    note: str = ""


class Audit:
    def __init__(self):
        self.seq_v3 = 0x200
        self.steps: List[Step] = []
        self.results: List[Result] = []
        self.rx_log: List[Tuple[float, str, bytes]] = []
        self.pending: Optional[Step] = None
        self.bus = None
        self.dev = None
        self.paths: Dict[str, str] = {}
        self.path_tag: Dict[str, str] = {}
        self.i = 0
        self.loop = None

    def next_seq(self) -> int:
        self.seq_v3 += 1
        return self.seq_v3

    def add_gets(self):
        keys = [
            ("01", "device info"), ("02", "func table"), ("03", "time"), ("04", "MAC"),
            ("05", "battery"), ("07", "func ex"), ("10", "notice status"), ("11", "unknown"),
            ("30", "DND"), ("A0", "live data"), ("A7", "flash"), ("B0", "brightness params"),
            ("B1", "weather switch"), ("B2", "unknown B2"), ("B3", "unknown B3"), ("F0", "MTU"),
            ("48", "firmware status"),
        ]
        for k, n in keys:
            self.steps.append(Step(f"GET {n}", f"GET 02 {k}", parse_hex(f"02 {k}"), "normal", f"classic:02{k}"))

    def add_v3_reads(self):
        self.steps.append(Step("v3 health sizes", "v3 05", build_v3_05(self.next_seq()), "bulk", "v3cmd:05", 1200))
        self.steps.append(Step("v3 get alarms", "v3 0F", v3_packet(0x0F, self.next_seq(), parse_hex("01 00 28")), "bulk", "v3cmd:0F", 2000))
        self.steps.append(Step("v3 dial list", "v3 06", v3_packet(0x06, self.next_seq(), bytes([0x01])), "bulk", "v3cmd:06", 1200))

    def add_v3_health_sync(self):
        for dtype in V3_TYPES:
            s = self.next_seq()
            self.steps.append(Step(f"v3 sync type {dtype:02X} start", f"v3 04 type {dtype:02X}", build_v3_04(s, 0, dtype), "bulk", f"v3type:{dtype:02X}", 1000))
            self.steps.append(Step(f"v3 sync type {dtype:02X} stop", f"v3 04 stop {dtype:02X}", build_v3_04(self.next_seq(), 1, dtype), "bulk", f"v3stop:{dtype:02X}", 300))

    def add_set_probes(self):
        # ACK-only probes with capture-safe OFF payloads where known
        safe = {
            "2A": "03 2A 55 55",
            "2D": "03 2D 55 00 00 00",
            "26": "03 26 01 1E",
            "49": "03 49 00 01 00 00 00 00 00 00 00",
            "35": "03 35 01 00 00 00 00 00 00 00 00 00",
            "30": "03 30 88 00 00 AA" + " 00" * 15,
        }
        keys = [
            "03", "04", "10", "11", "12", "13", "20", "21", "22", "23", "24", "25",
            "28", "29", "2A", "2B", "2C", "2D", "2E", "31", "32", "33", "35", "40",
            "41", "42", "43", "44", "45", "47", "49", "60", "E3",
        ]
        for k in keys:
            tx = parse_hex(safe[k]) if k in safe else parse_hex(f"03 {k}")
            self.steps.append(Step(f"SET 03 {k}", f"SET 03 {k}", tx, "normal", f"ack:03{k}", 800))

    def add_app_msg(self):
        self.steps.append(Step("MSG call end", "MSG 05 02", parse_hex("05 02 01"), "normal", "ack:0502", 500))
        self.steps.append(Step("APP music pause", "APP 06 01", parse_hex("06 01 01"), "normal", "any", 400))
        self.steps.append(Step("APP find device start", "APP 06 04", parse_hex("06 04 00"), "normal", "any", 800))
        self.steps.append(Step("APP find device stop", "APP 06 04", parse_hex("06 04 01"), "normal", "any", 400))
        # one-chunk test notification (may flash on watch)
        payload = b"GB audit test!!\x00"
        chunk = payload[:16].ljust(16, b"\x00")
        self.steps.append(Step("MSG notification", "MSG 05 03", bytes([0x05, 0x03, 1, 0]) + chunk, "normal", "any", 600))

    def on_rx(self, src, iface, changed, _inv):
        v = changed.get("Value")
        if v is None:
            return
        b = bytes(v)
        tag = self.path_tag.get(src, "?")
        self.rx_log.append((time.time(), tag, b))

    def write(self, ch: str, data: bytes):
        key = "write_normal" if ch == "normal" else "write_bulk"
        dbus.Interface(self.bus.get_object("org.bluez", self.paths[key]), probe.GATT_CHR).WriteValue(list(data), {})

    def match(self, step: Step, window: List[bytes]) -> Tuple[bool, List[str]]:
        rxs = [hx(b) for b in window]
        if step.expect == "any":
            return bool(window), rxs
        if step.expect.startswith("classic:"):
            pref = parse_hex(step.expect.split(":", 1)[1])
            ok = any(len(b) >= len(pref) and b[:len(pref)] == pref for b in window)
            return ok, rxs
        if step.expect.startswith("ack:"):
            pref = parse_hex(step.expect.split(":", 1)[1])
            ok = any(len(b) >= len(pref) and b[:len(pref)] == pref for b in window)
            return ok, rxs
        if step.expect.startswith("v3cmd:"):
            cmd = int(step.expect.split(":")[1], 16)
            ok = any(self._v3_has_cmd(b, cmd) for b in window)
            return ok, rxs
        if step.expect.startswith("v3type:"):
            dt = int(step.expect.split(":")[1], 16)
            ok = any(self._v3_sync_type(b, dt) or (b and b[0] == 0x33) for b in window)
            return ok, rxs
        if step.expect.startswith("v3stop:"):
            return bool(window), rxs
        return bool(window), rxs

    @staticmethod
    def _v3_has_cmd(b: bytes, cmd: int) -> bool:
        if len(b) >= 10 and b[0] == 0x33 and b[1] == 0xDA:
            return b[8] == (cmd & 0xFF) and b[9] == (cmd >> 8)
        return False

    @staticmethod
    def _v3_sync_type(b: bytes, dtype: int) -> bool:
        if Audit._v3_has_cmd(b, 0x04) and len(b) > 13:
            return b[13] == dtype
        return False

    def run_step(self):
        if self.i >= len(self.steps):
            self.finish()
            return False
        step = self.steps[self.i]
        self.pending = step
        t0 = time.time()
        self._step_t0 = t0
        self._rx_start = len(self.rx_log)
        ch = step.channel
        self.write(ch, step.tx)
        GLib.timeout_add(step.wait_ms, self.collect_step)
        return False

    def collect_step(self):
        step = self.pending
        window = [b for _, _, b in self.rx_log[self._rx_start:]]
        try:
            ok, rxs = self.match(step, window)
        except Exception as e:
            ok, rxs = False, [hx(b) for b in window[:3]]
            note = str(e)
        else:
            note = "" if ok else "no matching RX"
        self.results.append(Result(step.name, step.wire, "ok" if ok else "fail", hx(step.tx), rxs[:5], note))
        self.i += 1
        self.run_step()
        return False

    def finish(self):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "mac": MAC,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ok": sum(1 for r in self.results if r.status == "ok"),
            "fail": sum(1 for r in self.results if r.status == "fail"),
            "results": [r.__dict__ for r in self.results],
        }
        OUT.write_text(json.dumps(summary, indent=2))
        print(f"\nWrote {OUT}")
        print(f"OK {summary['ok']} / FAIL {summary['fail']} / total {len(self.results)}")
        for r in self.results:
            mark = "✓" if r.status == "ok" else "✗"
            print(f"  {mark} {r.wire}: {r.name}")
        try:
            self.dev.Disconnect()
        except Exception:
            pass
        self.loop.quit()

    def go(self, mac: str, scan: bool = True) -> int:
        if scan:
            subprocess.run(
                ["bluetoothctl", "--timeout", "15", "scan", "on"],
                capture_output=True, text=True,
            )
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        dev_path = probe.find_device(self.bus, mac)
        if not dev_path:
            print(f"Device {mac} not found")
            return 1
        self.dev = dbus.Interface(self.bus.get_object("org.bluez", dev_path), probe.DEV_IF)
        self.dev.Connect()
        for _ in range(50):
            if dbus.Interface(self.bus.get_object("org.bluez", dev_path), probe.PROP).Get(probe.DEV_IF, "Connected"):
                break
            time.sleep(0.2)
        chars = []
        for _ in range(30):
            chars = probe.chars_for_service(self.bus, probe.SVC)
            if len(chars) >= 4:
                break
            time.sleep(0.3)
        for path, uuid, _ in chars:
            self.path_tag[path] = uuid[4:8].upper()
            for name, u in probe.CHARS.items():
                if uuid.lower() == u.lower():
                    self.paths[name] = path
        for key in ("notify_normal", "notify_bulk"):
            p = self.paths[key]
            dbus.Interface(self.bus.get_object("org.bluez", p), probe.PROP).connect_to_signal(
                "PropertiesChanged", lambda *a, src=p: self.on_rx(src, *a))
            dbus.Interface(self.bus.get_object("org.bluez", p), probe.GATT_CHR).StartNotify()

        self.add_gets()
        self.add_v3_reads()
        self.add_v3_health_sync()
        self.add_set_probes()
        self.add_app_msg()
        print(f"Running {len(self.steps)} probes on {mac} …")
        self.loop = GLib.MainLoop()
        GLib.idle_add(self.run_step)
        self.loop.run()
        return 0 if all(r.status == "ok" for r in self.results) else 2


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac", default=MAC)
    ap.add_argument("--no-scan", action="store_true")
    a = ap.parse_args()
    sys.exit(Audit().go(a.mac, scan=not a.no_scan))
