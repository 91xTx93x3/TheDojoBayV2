import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from uptime import UptimeHistory


class UptimeHistoryTests(unittest.TestCase):
    def test_records_and_calculates_rolling_availability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "uptime.json"
            tracker = UptimeHistory(history_path)
            started = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)

            first = self._results("Active")
            tracker.record(first, started)
            second = self._results("Inactive")
            tracker.record(second, started + timedelta(minutes=10))

            node = second["mainnet"][0]
            self.assertEqual(node["uptime_30d"], 50.0)
            self.assertEqual(node["uptime_checks"], 2)
            self.assertEqual(node["uptime_since"], started.isoformat())

            with history_path.open() as source:
                persisted = json.load(source)
            self.assertEqual(len(next(iter(persisted["nodes"].values()))["samples"]), 2)

    def test_discards_samples_older_than_thirty_days(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = UptimeHistory(Path(tmpdir) / "uptime.json")
            started = datetime(2026, 7, 1, tzinfo=timezone.utc)
            tracker.record(self._results("Inactive"), started)

            current = self._results("Active")
            tracker.record(current, started + timedelta(days=31))

            self.assertEqual(current["mainnet"][0]["uptime_30d"], 100.0)
            self.assertEqual(current["mainnet"][0]["uptime_checks"], 1)

    @staticmethod
    def _results(status):
        return {
            "mainnet": [{
                "name": "Example",
                "pairing": {"url": "http://example.onion/v2"},
                "status": status,
            }],
            "testnet": [],
        }


if __name__ == "__main__":
    unittest.main()
