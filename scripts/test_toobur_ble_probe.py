#!/usr/bin/env python3
"""Unit tests for toobur_ble_probe pure helpers (no BLE hardware)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import toobur_ble_probe as probe


class ProbeHelpersTest(unittest.TestCase):
    def test_parse_hex(self):
        self.assertEqual(probe.parse_hex("02 05"), bytes([0x02, 0x05]))
        self.assertEqual(probe.parse_hex("0205"), bytes([0x02, 0x05]))

    def test_presets(self):
        self.assertEqual(probe.preset_tx("battery"), bytes([0x02, 0x05]))
        self.assertEqual(probe.preset_tx("notice"), bytes([0x02, 0x10]))
        self.assertEqual(probe.preset_tx("dnd"), bytes([0x02, 0x30]))

    def test_parse_battery(self):
        rx = bytes.fromhex("020500840E0009")
        info = probe.parse_battery(rx)
        self.assertIsNotNone(info)
        self.assertEqual(info["level_pct"], 9)
        self.assertEqual(info["voltage_mv"], 3716)
        self.assertEqual(info["status"], 0)

    def test_write_capture(self):
        with tempfile.TemporaryDirectory() as td:
            out = probe.write_capture(
                Path(td),
                label="battery",
                mac="AA:BB:CC:DD:EE:FF",
                tx=bytes([0x02, 0x05]),
                rx_list=[bytes.fromhex("020500840E0009")],
                backend="test",
            )
            text = out.read_text()
            self.assertIn("TX : 02 05", text)
            self.assertIn("RX : 02 05 00 84 0E 00 09", text)
            self.assertIn("battery", out.name)


if __name__ == "__main__":
    unittest.main()
