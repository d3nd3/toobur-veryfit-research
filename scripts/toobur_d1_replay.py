#!/usr/bin/env python3
"""Replay / mutate the official app's `D1` watch-face upload to the Toobur A200.

Extracted verbatim from `packetdumps/logcat/ui_watch_face_write_json.txt`:
announce, start, 401 data frames, finish. Replaying it byte-for-byte tests
whether our `D1` framing is right; `--mutate` then lets you patch bytes in the
transferred file (e.g. swap the background PNG) before sending.

The app's own `finish` is `D1 03 <3 checksum bytes> 00` — a bare `D1 03` is
rejected with `0x0B`, which is what made earlier probes look broken.

Examples:
  python3 scripts/toobur_d1_replay.py                       # verbatim replay
  python3 scripts/toobur_d1_replay.py --list-after          # then list dials
  python3 scripts/toobur_d1_replay.py --patch "silly.png=image1.png"
"""
from __future__ import annotations

import argparse
import dbus
import dbus.mainloop.glib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toobur_gatt_dump import (  # noqa: E402
    DEFAULT_MAC,
    DEV_IF,
    PRELUDE_GET,
    connect,
    send_cmd,
)

REPO = Path(__file__).resolve().parents[1]
CAPTURE = REPO / "packetdumps" / "logcat" / "ui_watch_face_write_json.txt"
ADAPTER = "/org/bluez/hci0"
D1_HDR = 7  # D1 02 + 5 unexplained bytes


def hx(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def bulk_send(bus, path: str, frames, gap: float = 0.0, listen: float = 0.0):
    """Write every frame inside ONE GLib main loop, collecting acks as they land.

    Doing this per-frame (spinning up a main loop and re-subscribing to
    PropertiesChanged 401 times) is slow enough that the watch drops the link
    partway through, so notifications are subscribed once and the writes are
    pumped from an idle callback.
    """
    import gi
    from gi.repository import GLib

    from toobur_gatt_dump import GATT_CHR, OM, WRITE_NORMAL

    write_p, notes = None, []
    for p, i in _managed(bus).items():
        if GATT_CHR not in i:
            continue
        u = str(i[GATT_CHR].get("UUID")).lower()
        if u == WRITE_NORMAL:
            write_p = p
        elif u in ("00000af7-0000-1000-8000-00805f9b34fb", "00000af2-0000-1000-8000-00805f9b34fb"):
            notes.append(p)
    if not write_p:
        raise SystemExit("no 0x0AF6 write characteristic")

    acks: list[tuple[int, int, int]] = []
    state = {"i": 0, "dead": None}

    def on_prop(_iface, changed, _inv):
        v = changed.get("Value")
        if v is None:
            return
        b = bytes(bytearray(v))
        if b[:2] == b"\xD1\x02":
            st = b[2] if len(b) > 2 else -1
            off = int.from_bytes(b[7:11], "little") if len(b) >= 11 else 0
            acks.append((state["i"], st, off))

    subs = []
    for p in notes:
        o = bus.get_object("org.bluez", p)
        subs.append(
            dbus.Interface(o, "org.freedesktop.DBus.Properties").connect_to_signal(
                "PropertiesChanged", on_prop
            )
        )
        try:
            dbus.Interface(o, GATT_CHR).StartNotify()
        except Exception:
            pass

    wobj = dbus.Interface(bus.get_object("org.bluez", write_p), GATT_CHR)
    loop = GLib.MainLoop()

    def pump():
        if state["i"] >= len(frames):
            # all frames written — drain for a moment so late acks land
            GLib.timeout_add(int(max(listen, 2.0) * 1000), loop.quit)
            return False
        i = state["i"]
        state["i"] = i + 1
        try:
            # Write-with-response, not without: the watch's RX buffer overruns
            # (and it drops the link) if we blast 401 frames back to back, and the
            # per-frame round trip is exactly the pacing the official app relies on.
            wobj.WriteValue(list(frames[i]), {})
        except dbus.exceptions.DBusException as e:
            state["dead"] = str(e)
            loop.quit()
            return False
        if (i + 1) % 50 == 0:
            print(f"   {i+1}/{len(frames)} sent, {len(acks)} acks", flush=True)
        return True

    GLib.timeout_add(max(1, int(gap * 1000)), pump) if gap else GLib.idle_add(pump)
    # safety net only — must exceed (frames * gap) or it truncates the send
    GLib.timeout_add(int((len(frames) * max(gap, 0.005) + 30) * 1000), loop.quit)
    loop.run()
    for p in notes:
        try:
            dbus.Interface(bus.get_object("org.bluez", p), GATT_CHR).StopNotify()
        except Exception:
            pass
    if state["dead"]:
        print(f"   LINK DIED after {state['i']}/{len(frames)} frames: {state['dead']}",
              file=sys.stderr)
    return acks


def _managed(bus):
    from toobur_gatt_dump import OM

    return dbus.Interface(bus.get_object("org.bluez", "/"), OM).GetManagedObjects()


def load_capture():
    """Pull the D1 upload sequence out of the app's logcat.

    The real transfer is the 137-byte frames plus one short tail frame. The two
    4-byte `D1 02 00 00` / `D1 02 00 EE` frames in the log are NOT file data --
    including them inflates the payload by 2 bytes and breaks the check code.
    """
    rx = re.compile(r"TX\s*:\s*([0-9A-F]{2}(?: [0-9A-F]{2})*)")
    frames = []
    for line in CAPTURE.open(errors="replace"):
        m = rx.search(line)
        if m:
            b = bytes.fromhex(m.group(1))
            if b[0] == 0xD1:
                frames.append(b)
    ann = [b for b in frames if b[1] == 1][0]
    start = [b for b in frames if b[1] == 5][0]
    data = [b for b in frames if b[1] == 2 and len(b) >= 71]
    size = int.from_bytes(ann[3:7], "little")
    payload = b"".join(f[3:] for f in data)
    if len(payload) != size:
        print(f"  WARNING: payload {len(payload)} B != announced size {size} B", file=sys.stderr)
    return ann, start, data, size, payload


def finish_frame(payload: bytes) -> bytes:
    """`D1 03 <check:u32 LE>` where check = additive byte sum of the payload.

    Solved against the official capture: sum() over the 53,802 announced bytes
    is 5,008,679 = 0x004C6D27, exactly the captured value. It is NOT CRC32 --
    the vendor library exports crc32/crc16 for the v3 frames, but the D1
    end-of-transfer check is a plain additive sum. The v3-style running value in
    each `D1 02` ack is the same sum, cumulative.
    """
    return bytes([0xD1, 0x03]) + (sum(payload) & 0xFFFFFFFF).to_bytes(4, "little")


def rebuild(data, new_file: bytes):
    """Re-frame a replacement file into the app's 137-byte D1 02 shape.

    The 5 header bytes after `D1 02` are not understood, so they are copied
    verbatim from the matching original frame. That is only valid while the
    payload length is unchanged (137 B frames).
    """
    if len(new_file) != len(b"".join(f[D1_HDR:] for f in data)) - 1:
        raise SystemExit(
            f"replacement is {len(new_file)} B but the captured stream is "
            f"{len(b''.join(f[D1_HDR:] for f in data)) - 1} B — header bytes are "
            "position-dependent, so the length must match. Pad or trim first."
        )
    out, pos = [], 0
    for f in data:
        chunk = new_file[pos : pos + 137 - D1_HDR]
        pos += len(chunk)
        out.append(f[:D1_HDR] + chunk)
    return out


def upload_once(bus, path, ann, start, data, finish, args):
    """One announce -> start -> data -> finish attempt. Returns (ok, acks)."""
    import dbus.mainloop.glib  # noqa: F811
    from toobur_gatt_dump import DEV_IF, PROP

    def connected() -> bool:
        try:
            return bool(
                dbus.Interface(bus.get_object("org.bluez", path), PROP).Get(DEV_IF, "Connected")
            )
        except Exception:
            return False

    for tag, pkt in (
        ("conn param 0", bytes.fromhex("03 35 00 00 00 00 00 00 00 00 00 00")),
        ("conn param 1", bytes.fromhex("03 35 01 00 00 00 00 00 00 00 00 00 00")),
        ("MTU", bytes.fromhex("02 F0")),
    ):
        send_cmd(bus, path, pkt, wait=0.7)

    print(f"-- announce ({len(ann)} B)")
    for r in send_cmd(bus, path, ann, wait=1.5):
        if r[:2] == b"\xD1\x01":
            print(f"   RX {hx(r[:8])}  {'OK' if r[2] == 0 else 'REJECTED'}")
            break

    print(f"-- start    ({len(start)} B)")
    for r in send_cmd(bus, path, start, wait=1.5):
        if r[:2] == b"\xD1\x05":
            print(f"   RX {hx(r[:8])}")
            break

    print(f"-- data     ({len(data)} frames)")
    acks = bulk_send(bus, path, data, args.gap, args.chunk_wait)
    real = [a for a in acks if a[1] == 0 and a[2] > 0]
    print(f"   {len(acks)} acks, {len(real)} successful, last offset "
          f"{acks[-1][2] if acks else 0}")

    if not connected():
        print("   link down before finish", file=sys.stderr)
        return False, acks

    print(f"-- finish   ({len(finish)} B)  check={int.from_bytes(finish[2:6], 'little')}")
    fin = None
    for r in send_cmd(bus, path, finish, wait=3.0):
        if r[:2] == b"\xD1\x03":
            fin = r
            break
    if fin is None:
        print("   no finish reply", file=sys.stderr)
        return False, acks
    print(f"   RX {hx(fin[:8])}  -> {'SUCCESS' if fin[2] == 0 else f'FAILED status={fin[2]:#04x}'}")
    return fin[2] == 0, acks


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay the app's D1 watch-face upload")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument(
        "--patch",
        metavar="NEW=ORIG",
        help="replace the container entry ORIG with bytes from NEW (e.g. silly.png=image1.png)",
    )
    ap.add_argument("--gap", type=float, default=0.02, help="seconds between data frames")
    ap.add_argument("--chunk-wait", type=float, default=0.0, help="seconds to listen after each frame")
    ap.add_argument("--announce", default="0af0", help="BLE service/char to use (informational)")
    ap.add_argument(
        "--name",
        help="override the announced name, e.g. silly1.iwf.lz (the capture used witch2.iwf.lz)",
    )
    ap.add_argument(
        "--finish-hex",
        help="override the finish frame payload after 'D1 03', e.g. '00000000' to probe",
    )
    ap.add_argument("--finish-tries", type=int, default=1, help="send finish N times")
    ap.add_argument("--list-after", action="store_true", help="query the dial list when done")
    ap.add_argument("--retries", type=int, default=4, help="reconnect+redo attempts")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ann, start, data, size, payload = load_capture()
    finish = finish_frame(payload)
    if args.name:
        nm = args.name.encode()
        ann = bytes.fromhex("D1 01 FF 2A D2 00 00 02") + nm
    if args.finish_hex:
        finish = bytes.fromhex("D1 03") + bytes.fromhex(args.finish_hex.replace(" ", ""))
    filebytes = payload
    print(f"capture: announce={len(ann)}B start={len(start)}B data={len(data)} frames "
          f"payload={len(payload)}B (announced {size}) magic={payload[5:10]!r}")
    print(f"  check code = sum(payload) = {sum(payload)} = {sum(payload):#010x}")
    print(f"  announce {hx(ann)}")
    print(f"           name = {ann[7:]!r}")
    print(f"  start    {hx(start)}")
    print(f"  finish   {hx(finish)}   (3 checksum bytes + 0x00 — a bare D1 03 fails)")

    if args.patch:
        new_p, _, orig = args.patch.partition("=")
        blob = Path(new_p).read_bytes()
        # locate ORIG entry inside the container by its name appearing in the stream
        idx = filebytes.find(orig.encode())
        if idx < 0:
            raise SystemExit(f"entry name {orig!r} not found in the container stream")
        print(f"patching {orig!r} at stream offset {idx} with {len(blob)} B from {new_p}")
        if len(blob) > len(filebytes) - idx:
            raise SystemExit("replacement too large for the space available")
        filebytes = filebytes[:idx] + blob + filebytes[idx + len(blob) :]
        data = rebuild(data, filebytes)

    if args.dry_run:
        print("dry run, nothing sent")
        return 0

    import dbus.mainloop.glib  # noqa: F811

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    ok = False
    for attempt in range(1, args.retries + 1):
        conn, path = connect(bus, args.mac, ADAPTER)
        if not conn:
            print(f"attempt {attempt}: connect failed", file=sys.stderr)
            time.sleep(3)
            continue
        time.sleep(2)
        for n, pkt in PRELUDE_GET:
            print(f"-- prelude {n}", file=sys.stderr)
            send_cmd(bus, path, pkt, wait=0.7)
        print(f"\n===== attempt {attempt}/{args.retries} =====")
        ok, _ = upload_once(bus, path, ann, start, data, finish, args)
        if ok:
            break
        print(f"attempt {attempt} did not complete; reconnecting", file=sys.stderr)
        try:
            dbus.Interface(bus.get_object("org.bluez", path), DEV_IF).Disconnect()
        except Exception:
            pass
        time.sleep(4)

    print(f"\n==== RESULT: {'SUCCESS' if ok else 'FAILED'} ====")

    if args.list_after:
        from toobur_dial import get_list

        time.sleep(2)
        print("\n== dial list ==")
        for d in get_list(bus, path, 0x0600, 2.5):
            mark = "  <== ACTIVE" if d["active"] else ""
            print(f"   type={d['type']:>3}  {d['name']!r}{mark}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
