#!/usr/bin/env python3
"""Pull-to-refresh smoke test — mimics VeryFit v3 health sync.

Quick (default): GET 02 01, GET 02 05, v3 cmd 05 on bulk.
Full (--full): prelude + 05 + per-type 04 START/STOP on normal (VeryFit order, save offsets).

Uses BlueZ D-Bus (same transport as toobur_ble_probe / toobur_bind_v3).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import toobur_ble_probe as probe
import toobur_bind_v3 as bind
import toobur_v3_sync as v3s

MAC = probe.MAC
OFFSETS_FILE = ROOT / "packetdumps" / "live" / "v3_sync_offsets.json"
CONN_FAST = bytes([0x03, 0x35, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
CONN_SLOW = bytes([0x03, 0x35, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def hx(bs: bytes) -> str:
    return " ".join(f"{b:02X}" for b in bs)


def parse_device_info(data: bytes) -> dict | None:
    if len(data) < 8 or data[0] != 0x02 or data[1] != 0x01:
        return None
    return {
        "device_id": data[2] | (data[3] << 8),
        "fw": data[4],
        "mode": data[5],
        "batt_status": data[6],
        "level_pct": data[7],
    }


class Smoke:
    def __init__(
        self,
        mac: str,
        sizes_timeout_s: float,
        seq: int,
        full: bool,
        offsets_path: Path,
        save_offsets: bool,
    ):
        self.mac = mac
        self.sizes_timeout_ms = int(sizes_timeout_s * 1000)
        self.seq = seq
        self.full = full
        self.offsets_path = offsets_path
        self.save_offsets = save_offsets
        self.offsets = v3s.load_offsets(offsets_path)
        self.rx: list[tuple[str, bytes]] = []
        self.bus = None
        self.dev = None
        self.paths: dict[str, str] = {}
        self.tags: dict[str, str] = {}
        self.loop = None
        self.step = 0
        self.fail = False
        self.plan: list[tuple[str, str, bytes, int]] = []
        self._dtype_start: int | None = None

    def on_rx(self, src, _if, chg, _inv):
        v = chg.get("Value")
        if v is not None:
            t = self.tags.get(src, "?")
            b = bytes(v)
            self.rx.append((t, b))
            print(f"RX [{t}]: {hx(b)[:140]}{'…' if len(b) > 48 else ''}")

    def w(self, ch: str, data: bytes):
        k = "write_normal" if ch == "normal" else "write_bulk"
        tag = "0AF6" if ch == "normal" else "0AF1"
        dbus.Interface(self.bus.get_object("org.bluez", self.paths[k]), probe.GATT_CHR).WriteValue(
            list(data), {}
        )
        print(f"TX [{tag}]: {hx(data)[:100]}{'…' if len(data) > 50 else ''}")

    def connect(self) -> bool:
        dp = probe.find_device(self.bus, self.mac)
        if not dp:
            print(f"{self.mac} not found — run: bluetoothctl scan on")
            return False
        self.dev = dbus.Interface(self.bus.get_object("org.bluez", dp), probe.DEV_IF)
        try:
            self.dev.Connect()
        except dbus.exceptions.DBusException as e:
            if "AlreadyConnected" not in str(e):
                print(f"Connect failed: {e}")
                return False
        for _ in range(50):
            if dbus.Interface(self.bus.get_object("org.bluez", dp), probe.PROP).Get(
                probe.DEV_IF, "Connected"
            ):
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
        missing = [k for k in probe.CHARS if k not in self.paths]
        if missing:
            print(f"Missing GATT chars: {missing}")
            return False
        for nk in ("notify_normal", "notify_bulk"):
            p = self.paths[nk]
            dbus.Interface(self.bus.get_object("org.bluez", p), probe.PROP).connect_to_signal(
                "PropertiesChanged", lambda *a, src=p: self.on_rx(src, *a)
            )
            dbus.Interface(self.bus.get_object("org.bluez", p), probe.GATT_CHR).StartNotify()
        return True

    def disconnect(self):
        for nk in ("notify_normal", "notify_bulk"):
            try:
                dbus.Interface(self.bus.get_object("org.bluez", self.paths[nk]), probe.GATT_CHR).StopNotify()
            except Exception:
                pass
        try:
            self.dev.Disconnect()
        except Exception:
            pass

    def build_plan(self):
        self.plan = [
            ("GET device info 02 01", "normal", bytes([0x02, 0x01]), 2500),
            ("GET battery 02 05", "normal", bytes([0x02, 0x05]), 2500),
        ]
        if self.full:
            self.plan.append(("SET conn param fast 03 35 01", "normal", CONN_FAST, 800))
        s = self.seq
        self.plan.append(
            (
                "v3 health sizes 05",
                v3s.v3_channel(v3s.build_v3_05(s, self.offsets)),
                v3s.build_v3_05(s, self.offsets),
                self.sizes_timeout_ms,
            )
        )
        if not self.full:
            return
        seq = s + 1
        for dtype in v3s.V3_SYNC_ORDER:
            save = self.offsets.get(dtype, 0)
            start = v3s.build_v3_04(seq, 0, dtype, save)
            self.plan.append((f"v3 sync type {dtype:02X} start off={save}", "normal", start, 3500))
            seq += 1
            stop = v3s.build_v3_04(seq, 1, dtype, 0)
            self.plan.append((f"v3 sync type {dtype:02X} stop", "normal", stop, 1500))
            seq += 1
        self.seq = seq
        if self.full:
            self.plan.append(("SET conn param slow 03 35 02", "normal", CONN_SLOW, 800))

    def run_steps(self):
        if self.step >= len(self.plan):
            self.finish()
            return False
        name, ch, pkt, wait_ms = self.plan[self.step]
        if " start " in name and "type " in name:
            self._dtype_start = int(name.split("type ")[1][:2], 16)
        else:
            self._dtype_start = None
        print(f"\n=== Step {self.step + 1}/{len(self.plan)}: {name} ===")
        n0 = len(self.rx)
        self.w(ch, pkt)
        GLib.timeout_add(wait_ms, self.check_step, name, pkt, n0)
        return False

    def _match_v3(self, pkt: bytes, window: list[tuple[str, bytes]]) -> tuple[bool, bytes | None]:
        if pkt[0] != 0x33 or len(pkt) < 10:
            return False, None
        want_cmd = pkt[8] | (pkt[9] << 8)
        want_seq = pkt[10] | (pkt[11] << 8)
        for _, b in window:
            if v3s.v3_cmd(b) != want_cmd or v3s.v3_nseq(b) != want_seq:
                continue
            return True, b
        return False, None

    def check_step(self, name, pkt, n0):
        window = [(t, b) for t, b in self.rx[n0:]]
        ok = False
        note = ""

        if pkt[:2] == bytes([0x02, 0x01]):
            info = next((parse_device_info(b) for _, b in window if parse_device_info(b)), None)
            if info:
                ok = True
                labels = {0: "normal", 1: "charging", 2: "full", 3: "LOW POWER"}
                note = (
                    f"id=0x{info['device_id']:04X} fw={info['fw']} "
                    f"batt={info['batt_status']}({labels.get(info['batt_status'], '?')}) "
                    f"{info['level_pct']}%"
                )
        elif pkt[:2] == bytes([0x02, 0x05]):
            info = next((probe.parse_battery(b) for _, b in window if probe.parse_battery(b)), None)
            if info:
                ok = True
                note = f"{info['level_pct']}% {info['voltage_mv']}mV status={info['status']}"
        elif pkt[0] == 0x33:
            ok, rx = self._match_v3(pkt, window)
            if ok and rx:
                cmd = v3s.v3_cmd(rx)
                if cmd == 0x05:
                    note = f"totalBytes={v3s.v3_total_05(rx)}"
                elif cmd == 0x04:
                    dt = v3s.v3_dtype(rx) or 0
                    note = f"dtype=0x{dt:02X} op={rx[12] if len(rx) > 12 else '?'}"
                    if dt == 0x02 and pkt[12] == 0x00:
                        p = v3s.parse_pressure_04(rx)
                        if p and p["samples"]:
                            s = p["samples"][0]
                            note += (
                                f" stress={s['value']} ({s.get('zone') or '?'})"
                                f" @+{s['delta']}min from min {p['start_min']}"
                            )
                            if p.get("average") is not None:
                                note += f" day avg={p['average']} range={p['min']}-{p['max']}"
                            v3s.bump_offset(self.offsets, 0x02, p["item_count"])
                    elif pkt[12] == 0x00 and dt in self.offsets:
                        # bump sport/spo2/hr from item_count when present
                        if len(rx) >= 19:
                            ic = rx[17] | (rx[18] << 8)
                            v3s.bump_offset(self.offsets, dt, ic)
            if not ok:
                note = f"no v3 0x{pkt[8]:02X} reply ({len(window)} pkts)"
        elif pkt[:2] == bytes([0x03, 0x35]):
            ok = any(len(b) >= 2 and b[0] == 0x03 and b[1] == 0x35 for _, b in window)
        else:
            ok = len(window) > 0

        if note:
            print(f"  {note}")
        print(f"  → {'PASS' if ok else 'FAIL'} {name}")
        if not ok:
            self.fail = True
        self.step += 1
        self.run_steps()
        return False

    def finish(self):
        if self.save_offsets and self.full:
            v3s.save_offsets(self.offsets_path, self.offsets)
            print(f"\nSaved offsets → {self.offsets_path}")
            print("  " + ", ".join(f"0x{k:02X}={v}" for k, v in sorted(self.offsets.items())))
        self.disconnect()
        if self.loop:
            self.loop.quit()

    def go(self) -> int:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        if not self.connect():
            return 1
        self.build_plan()
        mode = "full VeryFit sync" if self.full else "sizes probe"
        print(f"Connected {self.mac} — {mode}, sizes timeout {self.sizes_timeout_ms} ms\n")
        if self.full:
            print("Offsets: " + ", ".join(f"0x{k:02X}={v}" for k, v in sorted(self.offsets.items())))
        self.loop = GLib.MainLoop()
        GLib.idle_add(self.run_steps)
        self.loop.run()
        return 2 if self.fail else 0


def _selftest_fixture() -> int:
    lines = (ROOT / "packetdumps/logcat/sync_pressure_d7_2026-06-22.txt").read_text().splitlines()
    rx = probe.parse_hex(next(l.split(":", 1)[1] for l in lines if l.startswith("RX :")))
    p = v3s.parse_pressure_04(rx)
    if not p or p["samples"][0]["value"] != 0x10 or p["samples"][0]["zone"] != "relax":
        print("fixture parse failed", p)
        return 1
    print(
        f"fixture OK: stress={p['samples'][0]['value']} zone={p['samples'][0]['zone']} "
        f"avg={p['average']} range={p['min']}-{p['max']}"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="TOOBUR pull-to-refresh / v3 sync smoke test")
    ap.add_argument("--mac", default=MAC)
    ap.add_argument("--sizes-timeout", type=float, default=8.0)
    ap.add_argument("--seq", type=lambda x: int(x, 0), default=0xD2, help="v3 nseq for 0x05")
    ap.add_argument("--full", action="store_true", help="full 05 + all 04 types (VeryFit order)")
    ap.add_argument("--offsets", type=Path, default=OFFSETS_FILE)
    ap.add_argument("--no-save-offsets", action="store_true")
    ap.add_argument("--test-fixture", action="store_true", help="parse logcat pressure fixture only")
    args = ap.parse_args()
    if args.test_fixture:
        return _selftest_fixture()
    return Smoke(
        args.mac,
        args.sizes_timeout,
        args.seq,
        args.full,
        args.offsets,
        not args.no_save_offsets,
    ).go()


if __name__ == "__main__":
    sys.exit(main())
