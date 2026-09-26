#!/usr/bin/env python3
"""Make a deliberately silly watch face and sideload it to the Toobur A200.

Takes a known-good `.iwf.lz` payload (the exact bytes the official app streams),
applies **same-length** in-place patches, rebuilds the `D1` frames, recomputes the
end-of-transfer check, and uploads. Then optionally activates it.

Same-length patches are the safe subset: every byte offset, TOC entry and blob
length in the container is untouched, so nothing can desync. Only the declared
content changes.

Examples:
  python3 scripts/toobur_silly_face.py --dry-run
  python3 scripts/toobur_silly_face.py --activate
  python3 scripts/toobur_silly_face.py --name hax.iwf.lz --colour 0xFF00FF00
  python3 scripts/toobur_silly_face.py --patch 0xFFFF00FF=0xFF70F9F0
"""
from __future__ import annotations

import argparse
import dbus
import dbus.mainloop.glib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toobur_d1_replay import finish_frame, load_capture  # noqa: E402
from toobur_gatt_dump import (  # noqa: E402
    DEFAULT_MAC,
    DEV_IF,
    PRELUDE_GET,
    connect,
    send_cmd,
)
import importlib  # noqa: E402

_replay = importlib.import_module("toobur_d1_replay")

ADAPTER = "/org/bluez/hci0"
CHUNK = 134  # D1 02 00 + 134 bytes == 137 == MTU

# Patches: (find, replace, description). All equal length by construction.
SILLY = [
    (b"0xFF70F9F0", b"0xFFFF00FF", "hour-digit colour cyan -> screaming magenta"),
    (b"yxr", b"hax", "author: yxr -> hax"),
    (b"witch2", b"s1LLY!", "in-dial name: witch2 -> s1LLY!"),
]

EXTRA = [
    (b"0xFFFFF5A5", b"0xFF00FF00", "step digits -> neon green"),
    (b"0xFFFFFFFF", b"0xFFFF00FF", "white -> magenta"),
    (b"true", b"tru3", "bluetooth:true -> tru3 (mischief)"),
]


def hx(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def apply_patches(payload: bytes, patches) -> bytes:
    out = bytearray(payload)
    applied = []
    for find, repl, desc in patches:
        if len(find) != len(repl):
            raise SystemExit(f"patch length mismatch: {find!r} -> {repl!r}")
        n = 0
        pos = 0
        while True:
            i = bytes(out).find(find, pos)
            if i < 0:
                break
            out[i : i + len(find)] = repl
            pos = i + len(find)
            n += 1
        applied.append((desc, find.decode("latin1"), repl.decode("latin1"), n))
    return bytes(out), applied


def frame_payload(payload: bytes):
    """`D1 02 00` + 134-byte chunks.

    The final chunk is sent SHORT, not zero-padded — the official capture ends on
    a 71-byte frame (3 header + 68 payload). Padding it would make the watch
    receive more bytes than the announced size and desync the transfer.
    """
    frames = []
    for off in range(0, len(payload), CHUNK):
        chunk = payload[off : off + CHUNK]
        frames.append(bytes([0xD1, 0x02, 0x00]) + chunk)
    return frames


def main() -> int:
    ap = argparse.ArgumentParser(description="Sideload a deliberately silly A200 watch face")
    ap.add_argument("--mac", default=DEFAULT_MAC)
    ap.add_argument("--name", default="silly1.iwf.lz", help="name to announce")
    ap.add_argument("--colour", default="0xFFFF00FF", help="replacement for the hour-digit ARGB")
    ap.add_argument("--patch", action="append", metavar="NEW=OLD",
                    help="extra same-length patch, repeatable")
    ap.add_argument("--plain", action="store_true", help="upload with no patches at all")
    ap.add_argument("--extra", action="store_true", help="also apply the wilder extra patches")
    ap.add_argument("--gap", type=float, default=0.006)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--activate", action="store_true", help="switch the watch to it afterwards")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ann, start, _data, size, payload = load_capture()
    print(f"base payload: {len(payload)} B (announced {size})  magic={payload[5:10]!r}")

    patches = [] if args.plain else list(SILLY)
    if not args.plain:
        patches[0] = (b"0xFF70F9F0", args.colour.encode(), "hour-digit colour")
    if args.extra:
        patches += EXTRA
    for p in args.patch or []:
        new, _, old = p.partition("=")
        if not old:
            raise SystemExit(f"--patch wants NEW=OLD, got {p!r}")
        patches.append((old.encode("latin1"), new.encode("latin1"), f"custom {old}->{new}"))

    new_payload, applied = apply_patches(payload, patches)
    for desc, f, r, n in applied:
        print(f"  patch {f!r} -> {r!r}  x{n:<3} ({desc})")
    if len(new_payload) != len(payload):
        raise SystemExit("length changed - refusing")

    frames = frame_payload(new_payload)
    check = sum(new_payload) & 0xFFFFFFFF
    ann_new = bytes.fromhex("D1 01 FF") + len(new_payload).to_bytes(4, "little") + b"\x02" + args.name.encode()
    finish = bytes([0xD1, 0x03]) + check.to_bytes(4, "little")
    print(f"\nrebuilt: {len(frames)} frames x {CHUNK}B  (tail {len(payload) % CHUNK or CHUNK}B)")
    print(f"announce: {hx(ann_new)}")
    print(f"start   : {hx(start)}")
    print(f"finish  : {hx(finish)}   (sum={check})")
    if args.dry_run:
        print("dry run, nothing sent")
        return 0

    class A:  # minimal shim for upload_once()
        gap = args.gap
        chunk_wait = 0.0

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
        ok, _ = _replay.upload_once(bus, path, ann_new, start, frames, finish, A)
        if ok:
            break
        try:
            dbus.Interface(bus.get_object("org.bluez", path), DEV_IF).Disconnect()
        except Exception:
            pass
        time.sleep(4)

    print(f"\n==== UPLOAD: {'SUCCESS' if ok else 'FAILED'} ====")
    if not ok:
        return 1

    from toobur_dial import get_list, set_dial

    dial = args.name[:-3] if args.name.endswith(".lz") else args.name
    time.sleep(2)
    print("\n== dial list ==")
    for d in get_list(bus, path, 0x0700, 2.5):
        mark = "  <== ACTIVE" if d["active"] else ""
        print(f"   type={d['type']:>3}  {d['name']!r}{mark}")
    if args.activate:
        print(f"\n== activate {dial!r} ==")
        set_dial(bus, path, 0x0800, dial, 2.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
