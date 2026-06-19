#!/usr/bin/env python3
"""Extract TX/RX hex lines from VeryFit logcat dumps into Toobur fixture files.

Usage:
  python3 scripts/extract_logcat_fixtures.py packetdumps/logcat/sync_example.txt
  python3 scripts/extract_logcat_fixtures.py packetdumps/logcat/sync_example.txt --label sleep_start --grep "data type:7"

Output: gadgetbridge/app/src/test/resources/toobur/fixtures/<stem>_<label>.{tx,rx}.hex
Lines are comment-prefixed with source file and line context.

When logcat lacks a feature, capture via live BLE probe (issue 022) instead.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO / "gadgetbridge/app/src/test/resources/toobur/fixtures"
TX_RX = re.compile(r"(TX|RX)\s*:\s*([0-9A-Fa-f\s]+)\s*$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("logcat", type=Path, help="logcat dump (packetdumps/logcat/…)")
    p.add_argument("--label", default="extract", help="fixture name suffix")
    p.add_argument("--grep", default="", help="only emit lines whose previous context matches this regex")
    p.add_argument("--out-dir", type=Path, default=FIXTURE_DIR)
    return p.parse_args()


def strip_leading_33(hex_bytes: bytes) -> bytes:
    if hex_bytes and hex_bytes[0] == 0x33:
        return hex_bytes[1:]
    return hex_bytes


def format_hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def main() -> int:
    args = parse_args()
    logcat = args.logcat if args.logcat.is_absolute() else REPO / args.logcat
    if not logcat.is_file():
        print(f"not found: {logcat}", file=sys.stderr)
        return 1

    grep = re.compile(args.grep) if args.grep else None
    stem = logcat.stem
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    context_lines: list[str] = []
    count = 0
    for line in logcat.read_text(encoding="utf-8", errors="replace").splitlines():
        context_lines.append(line)
        if len(context_lines) > 8:
            context_lines.pop(0)
        context = "\n".join(context_lines)
        if grep and not grep.search(context):
            continue
        m = TX_RX.search(line)
        if not m:
            continue
        direction = m.group(1).lower()
        raw = bytes(int(x, 16) for x in m.group(2).split())
        if direction == "rx" and raw[:5] == bytes([0x33, 0xDA, 0xAD, 0xDA, 0xAD]):
            raw = strip_leading_33(raw)
        suffix = f"_{count}" if count else ""
        out = out_dir / f"{stem}_{args.label}{suffix}.{direction}.hex"
        header = (
            f"# source: {logcat.relative_to(REPO) if logcat.is_relative_to(REPO) else logcat}\n"
            f"# direction: {direction.upper()}\n"
        )
        if context:
            header += f"# context: {context.strip()[:120]}\n"
        out.write_text(header + format_hex(raw) + "\n", encoding="utf-8")
        print(out)
        count += 1
    if count == 0:
        print("no TX/RX lines matched", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
