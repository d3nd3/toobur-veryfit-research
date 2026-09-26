"""VeryFit-like v3 health sync builders + parsers (cmd 05 / 04)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Execution order from protocol_v3_health_client sync_timer_handles (HR last).
V3_SYNC_ORDER = [0x01, 0x02, 0x04, 0x06, 0x07, 0x08, 0x03]
BYTE14 = {0x04: 0x00, 0x06: 0x00, 0x07: 0x00}
DEFAULT_OFFSETS: Dict[int, int] = {t: 0 for t in V3_SYNC_ORDER}


def crc16(data: bytes, off: int, ln: int) -> int:
    c = 0xFFFF
    for i in range(off, off + ln):
        c ^= data[i] << 8
        for _ in range(8):
            c = (((c << 1) ^ 0x1021) if c & 0x8000 else (c << 1)) & 0xFFFF
    return c


def v3_channel(pkt: bytes) -> str:
    return "bulk" if len(pkt) > 50 else "normal"


def build_v3_05(seq: int, offsets: Optional[Dict[int, int]] = None) -> bytes:
    """137 B health sizes — embed per-type save offsets (5 B each)."""
    off = dict(DEFAULT_OFFSETS)
    if offsets:
        off.update(offsets)
    p = bytearray(137)
    p[0:5] = bytes([0x33, 0xDA, 0xAD, 0xDA, 0xAD])
    p[5] = 0x01
    p[6:8] = bytes([0x88, 0x00])
    p[8:10] = bytes([0x05, 0x00])
    p[10:12] = bytes([seq & 0xFF, (seq >> 8) & 0xFF])
    o = 12
    for t in V3_SYNC_ORDER:
        p[o] = t
        v = off.get(t, 0)
        p[o + 1 : o + 5] = int(v).to_bytes(4, "little")
        o += 5
    c = crc16(bytes(p), 1, 134)
    p[135], p[136] = c & 0xFF, (c >> 8) & 0xFF
    return bytes(p)


def build_v3_04(seq: int, operate: int, dtype: int, save_offset: int = 0) -> bytes:
    """19 B START/STOP — save_offset is item index for day types (VeryFit resume)."""
    b14 = BYTE14.get(dtype, 0x01)
    p = bytearray(19)
    p[0:12] = bytes(
        [
            0x33,
            0xDA,
            0xAD,
            0xDA,
            0xAD,
            0x01,
            0x10,
            0x00,
            0x04,
            0x00,
            seq & 0xFF,
            (seq >> 8) & 0xFF,
        ]
    )
    p[12], p[13], p[14] = operate, dtype, b14
    p[15], p[16] = save_offset & 0xFF, (save_offset >> 8) & 0xFF
    c = crc16(bytes(p), 1, 16)
    p[17], p[18] = c & 0xFF, (c >> 8) & 0xFF
    return bytes(p)


def v3_cmd(rx: bytes) -> Optional[int]:
    if len(rx) >= 10 and rx[0] == 0x33:
        return rx[8] | (rx[9] << 8)
    return None


def v3_nseq(rx: bytes) -> Optional[int]:
    if len(rx) >= 12 and rx[0] == 0x33:
        return rx[10] | (rx[11] << 8)
    return None


def v3_dtype(rx: bytes) -> Optional[int]:
    if len(rx) >= 14 and rx[0] == 0x33:
        return rx[13]
    return None


def v3_total_05(rx: bytes) -> Optional[int]:
    if len(rx) < 15 or rx[0] != 0x33 or v3_cmd(rx) != 0x05:
        return None
    return rx[11] | (rx[12] << 8) | (rx[13] << 16) | (rx[14] << 24)


def stress_zone(value: int) -> Optional[str]:
    """VeryFit stress zone for score 1–99."""
    if value < 1:
        return None
    if value <= 29:
        return "relax"
    if value <= 59:
        return "low"
    if value <= 79:
        return "medium"
    if value <= 99:
        return "high"
    return None


def pressure_day_stats(values: List[int]) -> Dict[str, Optional[int]]:
    """Average and min–max range (VeryFit day summary)."""
    if not values:
        return {"average": None, "min": None, "max": None, "range": None}
    lo, hi = min(values), max(values)
    return {
        "average": round(sum(values) / len(values)),
        "min": lo,
        "max": hi,
        "range": hi - lo,
    }


def _pressure_samples_from_rx(rx: bytes, start_min: int, data_size: int) -> List[Dict]:
    """Parse delta-min + value pairs after the fixed day header."""
    if data_size < 2:
        return []
    # Samples sit at the tail: (delta_u8, value_u8) × (data_size // 2)
    n = data_size // 2
    base = len(rx) - n * 2
    if base < 34:
        return []
    out = []
    t = start_min
    for i in range(n):
        d, v = rx[base + i * 2], rx[base + i * 2 + 1]
        t += d
        out.append({"delta": d, "value": v, "end_min": t, "zone": stress_zone(v)})
    return out


def parse_pressure_04(rx: bytes) -> Optional[Dict]:
    """Parse v3 cmd 04 pressure/stress reply (data_type 0x02)."""
    if len(rx) < 41 or rx[0] != 0x33 or rx[13] != 0x02:
        return None
    item_count = rx[17] | (rx[18] << 8)
    data_size = rx[21] | (rx[22] << 8)
    year = rx[26] | (rx[27] << 8)
    month, day = rx[28], rx[29]
    start_min = rx[30] | (rx[31] << 8) | (rx[32] << 16) | (rx[33] << 24)
    samples = _pressure_samples_from_rx(rx, start_min, data_size)
    values = [s["value"] for s in samples if s["value"] > 0]
    out: Dict = {
        "item_count": item_count,
        "data_size": data_size,
        "date": f"{year:04d}-{month:02d}-{day:02d}",
        "start_min": start_min,
        "samples": samples,
        **pressure_day_stats(values),
    }
    return out


def load_offsets(path: Path) -> Dict[int, int]:
    if not path.is_file():
        return dict(DEFAULT_OFFSETS)
    raw = json.loads(path.read_text())
    return {int(k, 0): int(v) for k, v in raw.items()}


def save_offsets(path: Path, offsets: Dict[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({f"0x{k:02X}": v for k, v in sorted(offsets.items())}, indent=2) + "\n")


def bump_offset(offsets: Dict[int, int], dtype: int, item_count: int) -> None:
    if item_count > 0 and dtype in (0x01, 0x02, 0x03, 0x08):
        offsets[dtype] = offsets.get(dtype, 0) + item_count
