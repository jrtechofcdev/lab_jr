from __future__ import annotations

import base64
import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "scan.csv"
PARSER = ROOT / "lib" / "airodump_csv.py"

spec = importlib.util.spec_from_file_location("airodump_csv", PARSER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def decode(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")


class ParserTests(unittest.TestCase):
    def test_parses_access_points_and_comma_in_essid(self) -> None:
        aps, stations = module.parse(FIXTURE)
        self.assertEqual(3, len(aps))
        self.assertEqual("JR,LAB", aps[0].essid)
        self.assertEqual("AA:BB:CC:DD:EE:FF", stations[0].bssid)

    def test_secured_output_excludes_open_network(self) -> None:
        aps, stations = module.parse(FIXTURE)
        output = io.StringIO()
        with redirect_stdout(output):
            module.output_aps(aps, stations, secured_only=True)
        rows = [line.split("|") for line in output.getvalue().splitlines()]
        self.assertEqual(2, len(rows))
        by_bssid = {row[0]: row for row in rows}
        self.assertEqual("JR,LAB", decode(by_bssid["AA:BB:CC:DD:EE:FF"][7]))
        self.assertEqual("1", by_bssid["AA:BB:CC:DD:EE:FF"][6])

    def test_station_output_is_scoped_to_target_bssid(self) -> None:
        _, stations = module.parse(FIXTURE)
        output = io.StringIO()
        with redirect_stdout(output):
            module.output_stations(stations, "aa:bb:cc:dd:ee:ff")
        rows = output.getvalue().splitlines()
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0].startswith("11:22:33:44:55:66|"))

    def test_rejects_invalid_target_bssid(self) -> None:
        _, stations = module.parse(FIXTURE)
        with self.assertRaises(ValueError):
            module.output_stations(stations, "not-a-mac")


if __name__ == "__main__":
    unittest.main()
