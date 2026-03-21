#!/usr/bin/env python3
"""
Parse protocol decompilation output and emit a mapping for VBUS event names
to their command header bytes.

Usage:
  python parse_vbus_mapping.py protocol_util_vbus_evt_to_str.c sub_1ba1d0.c
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional


CASE_LABEL_RE = re.compile(r"^\s*case\s+(-?\d+)\s*:")
DEFAULT_LABEL_RE = re.compile(r"^\s*default:")
STRING_RETURN_RE = re.compile(r'^\s*return\s+"([^"]+)"\s*;')
ASSIGNMENT_RE = re.compile(r"^\s*(v(?:1[6-9]|2[0-3]))\s*=\s*([^;]+);")
INT_TOKEN = r"[+-]?(?:0x[0-9A-Fa-f]+|\d+)"
LITERAL_RE = re.compile(rf"^\(?\s*({INT_TOKEN})\s*\)?$")
RANGE_IF_RE = re.compile(
    r"\bif\b.*\ba2\b\s*([+-])\s*(0x[0-9A-Fa-f]+|\d+)\s*<\s*(0x[0-9A-Fa-f]+|\d+)",
    re.IGNORECASE,
)
END_OF_CASE_RE = re.compile(r"^\s*(?:break;|goto\s+LABEL_\d+;|default:|}\s*)$")

BYTE_SLOT_ORDER = ("v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23")
CAST_PREFIX_RE = re.compile(r"^\((?:unsigned|signed)[^)]+\)\s*", re.IGNORECASE)


def parse_int_literal(text: str) -> Optional[int]:
    """Parse a signed decimal/hex integer literal."""
    value = text.strip().rstrip()
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
    if not LITERAL_RE.fullmatch(value):
        return None
    return int(value, 0)


def normalize_expr(text: str) -> str:
    """Trim casts and redundant wrapping around a2-driven expressions."""
    value = text.strip().rstrip(";")
    while CAST_PREFIX_RE.match(value):
        value = CAST_PREFIX_RE.sub("", value, count=1).strip()
    while value.startswith("(") and value.endswith(")") and value.count("(") == value.count(")"):
        value = value[1:-1].strip()
    return value


def parse_slot_value_expression(raw_expr: str) -> Optional[Callable[[int], int]]:
    """
    Parse slot assignments into an evaluator function of event id.

    Supports:
      - literals
      - a2
      - a2 +/- <literal>
      - <literal> +/- a2
    """
    expr = normalize_expr(raw_expr).replace(" ", "")
    if expr == "a2":
        return lambda evt_id: evt_id

    m = re.fullmatch(rf"a2([+-])({INT_TOKEN})", expr)
    if m:
        op, raw_value = m.group(1), m.group(2)
        value = parse_int_literal(raw_value)
        if value is None:
            return None
        if op == "+":
            return lambda evt_id, value=value: evt_id + value
        return lambda evt_id, value=value: evt_id - value

    m = re.fullmatch(rf"({INT_TOKEN})([+-])a2", expr)
    if m:
        raw_value, op = m.group(1), m.group(2)
        value = parse_int_literal(raw_value)
        if value is None:
            return None
        if op == "+":
            return lambda evt_id, value=value: value + evt_id
        return lambda evt_id, value=value: value - evt_id

    value = parse_int_literal(expr)
    if value is not None:
        return lambda _evt_id, value=value: value
    return None


def parse_a2_range_from_condition(raw_line: str) -> Optional[List[int]]:
    """
    Parse branches like `(unsigned int)(a2 - N) < M`.
    """
    simplified = (
        raw_line.replace("(", " ")
        .replace(")", " ")
        .replace("\t", " ")
        .replace(";", " ")
    )
    match = RANGE_IF_RE.search(simplified)
    if not match:
        return None
    op, start_text, span_text = match.group(1), match.group(2), match.group(3)
    if op != "-":
        return None
    start = parse_int_literal(start_text)
    span = parse_int_literal(span_text)
    if start is None or span is None or span <= 0:
        return None
    return [start + offset for offset in range(span)]


def emit_header(entries: Dict[int, List[List[int]]], targets: List[int], slot_exprs: Dict[str, Callable[[int], int]]) -> None:
    """Emit resolved first-two-byte headers for each target event id."""
    for event_id in targets:
        header: List[int] = []
        for slot in BYTE_SLOT_ORDER:
            value_fn = slot_exprs.get(slot)
            if value_fn is None:
                continue
            try:
                value = value_fn(event_id)
            except Exception:
                continue
            header.append(to_byte(value))
            if len(header) == 2:
                break
        if header:
            entries[event_id].append(header[:2])


def to_byte(value: int) -> int:
    """Normalize command values to unsigned byte range for readability."""
    return value & 0xFF


def parse_vbus_names(path: Path) -> Dict[int, str]:
    """Extract event_id -> VBUS event string from the first C file."""
    names: Dict[int, str] = {}
    active_case: Optional[int] = None

    with path.open("r", encoding="utf-8", errors="ignore") as fp:
        for raw_line in fp:
            line = raw_line.strip()
            case_match = CASE_LABEL_RE.match(line)
            if case_match:
                active_case = int(case_match.group(1))
                continue

            if active_case is None:
                continue

            str_match = STRING_RETURN_RE.match(line)
            if str_match:
                event_name = str_match.group(1)
                if event_name.startswith("VBUS_"):
                    names[active_case] = event_name
                active_case = None

    return names


def parse_cmd_headers(path: Path) -> Dict[int, List[List[int]]]:
    """Extract event_id -> list of observed cmd header byte pairs from switch cases."""
    headers: Dict[int, List[List[int]]] = defaultdict(list)
    active_case: Optional[List[int]] = None
    active_exprs: Dict[str, Callable[[int], int]] = {}
    range_case: Optional[List[int]] = None
    range_exprs: Dict[str, Callable[[int], int]] = {}

    def flush_active() -> None:
        nonlocal active_case, active_exprs, range_case, range_exprs
        if active_case is not None and active_exprs:
            emit_header(headers, active_case, active_exprs)
        active_case = None
        active_exprs = {}
        if range_case is not None and range_exprs:
            emit_header(headers, range_case, range_exprs)
        range_case = None
        range_exprs = {}

    def flush_range_case() -> None:
        nonlocal range_case, range_exprs
        if range_case is not None and range_exprs:
            emit_header(headers, range_case, range_exprs)
        range_case = None
        range_exprs = {}

    with path.open("r", encoding="utf-8", errors="ignore") as fp:
        for raw_line in fp:
            line = raw_line.strip()
            case_match = CASE_LABEL_RE.match(line)
            if case_match:
                flush_active()
                active_case = [int(case_match.group(1))]
                continue

            if DEFAULT_LABEL_RE.match(line):
                flush_active()
                active_case = None
                active_exprs = {}
                continue

            if active_case is None and range_case is None:
                range_ids = parse_a2_range_from_condition(line)
                if range_ids is not None:
                    range_case = range_ids
                    range_exprs = {}
                    continue

            if active_case is None and range_case is None:
                continue

            assign = ASSIGNMENT_RE.match(line)
            if assign:
                var_name = assign.group(1)
                expr_fn = parse_slot_value_expression(assign.group(2))
                if expr_fn is None:
                    continue
                if range_case is not None:
                    range_exprs[var_name] = expr_fn
                else:
                    active_exprs[var_name] = expr_fn
                continue

            if END_OF_CASE_RE.match(line):
                if range_case is not None:
                    flush_range_case()
                if active_case is not None:
                    emit_header(headers, active_case, active_exprs)
                    active_case = None
                    active_exprs = {}

    flush_active()
    return headers


def build_mapping(
    names: Dict[int, str],
    headers: Dict[int, List[List[int]]],
    include_missing: bool,
    first_only: bool,
) -> List[Dict[str, object]]:
    """Build the final JSON-ready array."""
    rows: List[Dict[str, object]] = []
    for event_id in sorted(names):
        event_name = names[event_id]
        cmd_headers = headers.get(event_id, [])
        if not cmd_headers:
            if include_missing:
                rows.append(
                    {"eventName": event_name, "eventId": event_id, "cmdHeaderBytes": []}
                )
            continue
        if first_only:
            rows.append(
                {
                    "eventName": event_name,
                    "eventId": event_id,
                    "cmdHeaderBytes": cmd_headers[0],
                }
            )
            continue
        for idx, cmd_header in enumerate(cmd_headers, start=1):
            rows.append(
                {
                    "eventName": event_name,
                    "eventId": event_id,
                    "occurrence": idx,
                    "cmdHeaderBytes": cmd_header,
                }
            )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate VBUS event mappings from protocol decompilation files."
    )
    parser.add_argument("vbus_file", type=Path, help="protocol_util_vbus_evt_to_str.c")
    parser.add_argument("write_file", type=Path, help="sub_1ba1d0.c")
    parser.add_argument(
        "--include-missing",
        action="store_true",
        help="Include entries where no cmdHeaderBytes were found (empty list).",
    )
    parser.add_argument(
        "--first-only",
        action="store_true",
        help=(
            "If multiple cmd-header mappings exist for one event id, keep only the "
            "first one."
        ),
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for print output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = parse_vbus_names(args.vbus_file)
    headers = parse_cmd_headers(args.write_file)
    rows = build_mapping(names, headers, args.include_missing, args.first_only)
    print(json.dumps(rows, indent=args.indent, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
