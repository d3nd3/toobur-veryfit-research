#!/usr/bin/env python3
"""
Merge standalone evt / VBUS annotation lines onto their matching TX line.

Uses bruteforce_results.txt: each [VALID] / [HUH] line maps the first two hex bytes
after "TX >>>" to VBUS_EVT_* names on the *same* line only.

V3 frames (33 DA AD DA AD ...) use substring patterns from the V3 section / log shape.

After merging, any bare ``TX >>>`` line is prefixed with an inferred label:
``VBUS_EVT_*`` when mapped from bruteforce; otherwise a **neutral** wire label (no ``VBUS_`` /
``PROTOCOL_`` prefix — e.g. ``CMD_*``, ``V3_*``, ``TX_UNKNOWN``). No line may start with
``TX >>>`` alone.

Usage:
  python3 scripts/merge_vbus_tx_annotations.py packetdumps/logcat/reinstall_app_bind_stripped.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BRUTE = REPO / "bruteforce_results.txt"

TX_PREFIX = "TX >>> "
MERGE_SEP = "  "  # annotation + MERGE_SEP + TX line

# Naming: use ``VBUS_EVT_*`` only for bruteforce/mapped events; wire/V3 uses neutral names
# (no ``VBUS_`` / ``PROTOCOL_`` prefix).
TX_UNKNOWN = "TX_UNKNOWN"
CMD_BLE_CONTROL_07_40 = "CMD_BLE_CONTROL_07_40"
CMD_SET_03_E3_UNKNOWN = "CMD_SET_03_E3_UNKNOWN"
UNKNOWN_33_40_A5 = "UNKNOWN_33_40_A5"
V3_00_1A_GET_FUNC_TABLE = "V3_00_1A_GET_FUNC_TABLE"
V3_07_DIAL_OR_WRITE = "V3_07_DIAL_OR_WRITE"
V3_00_08_SET_DIAL = "V3_00_08_SET_DIAL"

# One-time renames for older stripped dumps / scripts
LEGACY_LABEL_RENAME: dict[str, str] = {
    "unknown": TX_UNKNOWN,
    "PROTOCOL_unknown": TX_UNKNOWN,
    "PROTOCOL_UNKNOWN": TX_UNKNOWN,
    "SET_03_E3_bruteforce_??": CMD_SET_03_E3_UNKNOWN,
    "PROTOCOL_CMD_SET_03_E3_unknown": CMD_SET_03_E3_UNKNOWN,
    "PROTOCOL_CMD_SET_03_E3_UNKNOWN": CMD_SET_03_E3_UNKNOWN,
    "TX_33_40_A5_not_in_bruteforce": UNKNOWN_33_40_A5,
    "PROTOCOL_UNKNOWN_33_40_A5": UNKNOWN_33_40_A5,
    "V3_00_1A_get_func_table_v3": V3_00_1A_GET_FUNC_TABLE,
    "PROTOCOL_V3_00_1A_GET_FUNC_TABLE": V3_00_1A_GET_FUNC_TABLE,
    "V3_cmd_0x07_dial_or_write": V3_07_DIAL_OR_WRITE,
    "PROTOCOL_V3_07_DIAL_OR_WRITE": V3_07_DIAL_OR_WRITE,
    "V3_00_08_IDOV3SetDial": V3_00_08_SET_DIAL,
    "PROTOCOL_V3_00_08_SET_DIAL": V3_00_08_SET_DIAL,
    "PROTOCOL_CMD_BLE_CONTROL_07_40": CMD_BLE_CONTROL_07_40,
}


def parse_bruteforce(path: Path) -> dict[str, set[tuple[str, str]]]:
    """Label -> set of (byte1, byte2): ``VBUS_EVT_*`` from file plus manual wire labels."""
    vbus_to_pairs: dict[str, set[tuple[str, str]]] = {}
    text = path.read_text(encoding="utf-8", errors="replace")

    def add(vbus: str, b1: str, b2: str) -> None:
        vbus_to_pairs.setdefault(vbus, set()).add((b1.upper(), b2.upper()))

    line_pat = re.compile(
        r"^\[(?:VALID|HUH\??)\]\s+([0-9A-Fa-f]{2})\s+([0-9A-Fa-f]{2})\s+-"
    )
    for line in text.splitlines():
        m = line_pat.match(line)
        if not m:
            continue
        b1, b2 = m.group(1), m.group(2)
        for vm in re.finditer(r"(VBUS_EVT_[A-Za-z0-9_]+)", line):
            add(vm.group(1), b1, b2)

    # V3 [VALID 00 09] - inner opcode
    v3_pat = re.compile(r"^\[VALID\s+([0-9A-Fa-f]{2})\s+([0-9A-Fa-f]{2})\]\s*-")
    for line in text.splitlines():
        m = v3_pat.match(line)
        if not m:
            continue
        b1, b2 = m.group(1), m.group(2)
        for vm in re.finditer(r"(VBUS_EVT_[A-Za-z0-9_]+)", line):
            add(vm.group(1), b1, b2)

    # MISSING_FROM_BRUTEFORCE block: "HH HH - VBUS_EVT_..."
    miss_pat = re.compile(
        r"^([0-9A-Fa-f]{2})\s+([0-9A-Fa-f]{2})\s+-\s+(VBUS_EVT_[A-Za-z0-9_]+)"
    )
    for line in text.splitlines():
        m = miss_pat.match(line.strip())
        if m:
            add(m.group(3), m.group(1), m.group(2))

    # Alias: table user uses same wire as GET_FUNC_TABLE
    if "VBUS_EVT_APP_GET_FUNC_TABLE" in vbus_to_pairs:
        vbus_to_pairs["VBUS_EVT_APP_GET_FUNC_TABLE_USER"] = set(
            vbus_to_pairs["VBUS_EVT_APP_GET_FUNC_TABLE"]
        )

    # Line 32: [VALID] 02 B1 - GET_WEATHER_SWITCH (no VBUS_EVT_* on that bruteforce line)
    vbus_to_pairs.setdefault("VBUS_EVT_APP_GET_WEATHER_SWITCH", set()).add(("02", "B1"))

    # bruteforce_results.txt: #define PROTOCOL_CMD_BLE_CONTROL 0x07 — observed first bytes 07 40 …
    vbus_to_pairs.setdefault(CMD_BLE_CONTROL_07_40, set()).add(("07", "40"))
    # Line 76: [VALID] 03 E3 - ?? (no VBUS name in file)
    vbus_to_pairs.setdefault(CMD_SET_03_E3_UNKNOWN, set()).add(("03", "E3"))
    # Short TX seen at end of bind; not in bruteforce table
    vbus_to_pairs.setdefault(UNKNOWN_33_40_A5, set()).add(("33", "40"))

    return vbus_to_pairs


# V3: match substring inside full hex body (33 DA AD ... frames)
# value = substring to find in TX hex body (avoid loose "00 0F" — it appears in 01 2A 00 08 … seq)
V3_SUBSTRING: dict[str, str] = {
    "VBUS_EVT_FUNC_V3_SET_HR_MODE": "01 17 00 09",
    "VBUS_EVT_FUNC_V3_GET_ALARM": "01 0C 00 0F",
    "VBUS_EVT_FUNC_V3_SPORT_SORT": "01 28 00 0C",
    "VBUS_EVT_FUNC_START_SYNC_V3_HEALTH": "01 88 00 05",
}

# bruteforce_results.txt V3 section line 267: [VALID] 00 1A - get func table v3
V3_GET_FUNC_TABLE_INNER = "00 1A"
# TOOBUR.md: v3 cmd 0x07 = dial/write JSON
V3_CMD_0X07_DIAL = "01 0B 00 07"
# bruteforce line 259: [VALID 00 08] - IDOV3SetDial; docs/v3_cmd08_layout.md: 01 2A 00 08 …
V3_IDOV3_SET_DIAL_FRAME = "01 2A 00 08"

# Auto labels that can be replaced when infer() improves
WEAK_TX_PREFIXES = frozenset(
    {
        TX_UNKNOWN,
        "unknown",  # legacy
        "PROTOCOL_unknown",  # legacy
        "PROTOCOL_UNKNOWN",  # legacy
        "V3_get_func_table_v3",
        "V3_01_2A_00_08",
    }
)

# Bruteforce lists 02 B1 GET_WEATHER_SWITCH without a VBUS line; evt 326 in log pairs with 02 B1
EVT326_VBUS = "VBUS_EVT_APP_GET_WEATHER_SWITCH"


def first_hex_pair(tx_line: str) -> tuple[str, str] | None:
    if not tx_line.startswith(TX_PREFIX):
        return None
    toks = tx_line[len(TX_PREFIX) :].strip().split()
    if len(toks) >= 2:
        return toks[0].upper(), toks[1].upper()
    return None


def tx_matches_vbus(tx_line: str, vbus: str, vbus_to_pairs: dict[str, set[tuple[str, str]]]) -> bool:
    body = tx_line[len(TX_PREFIX) :].strip() if tx_line.startswith(TX_PREFIX) else ""
    if not body:
        return False
    if vbus in V3_SUBSTRING:
        return V3_SUBSTRING[vbus] in body
    pairs = vbus_to_pairs.get(vbus)
    if not pairs:
        return False
    fp = first_hex_pair(tx_line)
    if fp and fp in pairs:
        return True
    # Early-window match for odd framing (e.g. 07 40)
    head = " ".join(body.split()[:24])
    for b1, b2 in pairs:
        if f"{b1} {b2}" in head:
            return True
    return False


ANN_RE = re.compile(r"^(\d+)\((VBUS_EVT_[A-Za-z0-9_]+)\)\s*$")
BARE_RE = re.compile(r"^(VBUS_EVT_[A-Za-z0-9_]+)\s*$")
NUM_RE = re.compile(r"^(\d+)\s*$")


def is_real_annotation(left: str) -> bool:
    """Only split merged lines for evt-number annotations (not bare VBUS or auto-inferred labels).

    Bare ``VBUS_EVT_*`` lines are merged by the script into ``VBUS_EVT_*  TX >>>``; those merged
    lines must **not** be split (would duplicate ``VBUS_EVT_FUNC_*`` from ``infer_bare_tx_label``).
    """
    s = left.strip()
    if ANN_RE.match(s):
        return True
    if NUM_RE.match(s) and s == "326":
        return True
    if s == "SET_BLE_EVT_CONNECT":
        return True
    return False


def collapse_orphan_auto_label_runs(lines: list[str]) -> list[str]:
    """Remove duplicate standalone auto-label lines left before a ``label  TX >>>`` line."""
    auto = frozenset(WEAK_TX_PREFIXES)
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if TX_PREFIX not in ln and s in auto:
            j = i
            while j < len(lines) and lines[j].strip() == s and TX_PREFIX not in lines[j]:
                j += 1
            if j < len(lines) and lines[j].strip().startswith(s + MERGE_SEP + TX_PREFIX.strip()):
                out.append(lines[j])
                i = j + 1
                continue
        out.append(ln)
        i += 1
    return out


def unmerge_lines(lines: list[str]) -> list[str]:
    """Split 'ANN  TX >>> ...' back to two lines (only for real annotations)."""
    out: list[str] = []
    for ln in lines:
        if MERGE_SEP + TX_PREFIX in ln and not ln.startswith("RX ") and ln.strip():
            left, right = ln.split(MERGE_SEP + TX_PREFIX, 1)
            left = left.rstrip()
            if is_real_annotation(left):
                out.append(left)
                out.append(TX_PREFIX + right)
            else:
                out.append(ln)
        else:
            out.append(ln)
    return out


def pair_to_primary_vbus(
    vbus_to_pairs: dict[str, set[tuple[str, str]]],
) -> dict[tuple[str, str], str]:
    """First VBUS name wins per (b1,b2) for stable reverse lookup."""
    inv: dict[tuple[str, str], str] = {}
    for vbus in sorted(vbus_to_pairs.keys()):
        for p in sorted(vbus_to_pairs[vbus]):
            inv.setdefault(p, vbus)
    return inv


def infer_bare_tx_label(
    tx_line: str,
    inv: dict[tuple[str, str], str],
) -> str:
    """Label for a bare ``TX >>>`` line (no merged annotation)."""
    if not tx_line.startswith(TX_PREFIX):
        return TX_UNKNOWN
    body = tx_line[len(TX_PREFIX) :].strip()
    if not body:
        return TX_UNKNOWN
    toks = body.split()
    # Standard command: first two hex bytes (07 40 BLE, 03 E3, 33 40, 02 xx, …)
    if len(toks) >= 2:
        p = (toks[0].upper(), toks[1].upper())
        if p in inv:
            return inv[p]
    # V3 wrapper 33 DA AD DA AD …
    if len(toks) >= 2 and toks[0] == "33" and toks[1] == "DA":
        # Order matters (see bruteforce_results.txt V3 section + TOOBUR.md)
        if V3_CMD_0X07_DIAL in body:
            return V3_07_DIAL_OR_WRITE
        if V3_GET_FUNC_TABLE_INNER in body:
            return V3_00_1A_GET_FUNC_TABLE
        if "01 17 00 09" in body:
            return "VBUS_EVT_FUNC_V3_SET_HR_MODE"
        if "01 0C 00 0F" in body:
            return "VBUS_EVT_FUNC_V3_GET_ALARM"
        if "01 28 00 0C" in body:
            return "VBUS_EVT_FUNC_V3_SPORT_SORT"
        if "01 88 00 05" in body:
            return "VBUS_EVT_FUNC_START_SYNC_V3_HEALTH"
        if V3_IDOV3_SET_DIAL_FRAME in body:
            return V3_00_08_SET_DIAL
    return TX_UNKNOWN


def normalize_legacy_tx_labels(lines: list[str]) -> list[str]:
    """Rewrite legacy label prefixes on merged ``ANN  TX >>>`` lines to current scheme."""
    out: list[str] = []
    for ln in lines:
        if MERGE_SEP + TX_PREFIX in ln and not ln.startswith("RX ") and ln.strip():
            left, right = ln.split(MERGE_SEP + TX_PREFIX, 1)
            key = left.strip()
            if key in LEGACY_LABEL_RENAME:
                ln = f"{LEGACY_LABEL_RENAME[key]}{MERGE_SEP}{TX_PREFIX}{right}"
        out.append(ln)
    return out


def relabel_weak_tx_prefixes(
    lines: list[str],
    inv: dict[tuple[str, str], str],
) -> list[str]:
    """Refresh labels for weak/legacy auto prefixes using current ``infer_bare_tx_label``."""
    out: list[str] = []
    for ln in lines:
        if MERGE_SEP + TX_PREFIX not in ln:
            out.append(ln)
            continue
        left, right = ln.split(MERGE_SEP + TX_PREFIX, 1)
        left = left.strip()
        tx = TX_PREFIX + right
        if left in WEAK_TX_PREFIXES:
            new_l = infer_bare_tx_label(tx, inv)
            out.append(f"{new_l}{MERGE_SEP}{tx}")
        else:
            out.append(ln)
    return out


def insert_blank_before_tx_lines(lines: list[str]) -> list[str]:
    """Insert one empty line before each line that contains ``TX >>>`` (if not already blank above)."""
    out: list[str] = []
    for ln in lines:
        if "TX >>>" in ln and out and out[-1].strip() != "":
            out.append("")
        out.append(ln)
    return out


def label_bare_tx_lines(
    lines: list[str],
    inv: dict[tuple[str, str], str],
) -> list[str]:
    """Prefix every bare ``TX >>>`` line with ``<label>  `` (use ``TX_UNKNOWN`` if not inferred)."""
    out: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith(TX_PREFIX):
            out.append(ln)
            continue
        if MERGE_SEP + TX_PREFIX in ln:
            # merged line: "ANN  TX >>> ..."
            out.append(ln)
            continue
        label = infer_bare_tx_label(s, inv)
        out.append(f"{label}{MERGE_SEP}{s}")
    return out


def collect_annotations(
    lines: list[str],
) -> list[tuple[int, str, str]]:
    """(line_index, full_annotation_text, vbus_for_matching)."""
    items: list[tuple[int, str, str]] = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("RX ") or s.startswith("=="):
            continue
        if s in ("unknown", TX_UNKNOWN, "PROTOCOL_UNKNOWN", "PROTOCOL_unknown"):
            continue
        if MERGE_SEP + TX_PREFIX in ln:
            continue
        m = ANN_RE.match(s)
        if m:
            items.append((i, s, m.group(2)))
            continue
        m = BARE_RE.match(s)
        if m:
            items.append((i, s, m.group(1)))
            continue
        m = NUM_RE.match(s)
        if m and m.group(1) == "326":
            items.append((i, s, EVT326_VBUS))
            continue
        if s == "SET_BLE_EVT_CONNECT":
            continue
    return items


def merge_file(path: Path, vbus_to_pairs: dict[str, set[tuple[str, str]]]) -> None:
    inv = pair_to_primary_vbus(vbus_to_pairs)
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    raw = collapse_orphan_auto_label_runs(raw)
    lines = unmerge_lines(raw)

    anns = collect_annotations(lines)
    anns.sort(key=lambda x: x[0])

    used_tx: set[int] = set()

    def find_tx(start: int, vbus: str) -> int | None:
        for j in range(start + 1, len(lines)):
            if not lines[j].startswith(TX_PREFIX):
                continue
            if j in used_tx:
                continue
            if MERGE_SEP + TX_PREFIX in lines[j]:
                continue
            if tx_matches_vbus(lines[j], vbus, vbus_to_pairs):
                return j
        return None

    # Apply merges from bottom line index up so deletions don't shift earlier indices
    for ann_idx, ann_text, vbus in sorted(anns, key=lambda x: x[0], reverse=True):
        if ann_idx >= len(lines) or lines[ann_idx].strip() != ann_text:
            continue
        txi = find_tx(ann_idx, vbus)
        if txi is None:
            continue
        used_tx.add(txi)
        tx_ln = lines[txi]
        lines[txi] = f"{ann_text}{MERGE_SEP}{tx_ln}"
        del lines[ann_idx]

    lines = label_bare_tx_lines(lines, inv)
    lines = relabel_weak_tx_prefixes(lines, inv)
    lines = normalize_legacy_tx_labels(lines)
    lines = insert_blank_before_tx_lines(lines)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path, nargs="?", default=REPO / "packetdumps/logcat/reinstall_app_bind_stripped.txt")
    args = ap.parse_args()
    vbus_map = parse_bruteforce(BRUTE)
    merge_file(args.file, vbus_map)
    print(f"Updated {args.file} ({len(vbus_map)} VBUS keys from {BRUTE.name})")


if __name__ == "__main__":
    main()
