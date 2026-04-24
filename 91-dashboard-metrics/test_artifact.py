"""
Edge-case tests for artifact.py. Uses stdlib unittest only, no pip install.

Run:
    python -m unittest test_artifact.py -v

Covers:
  1. planned_min == 0 returns 0.0 OEE instead of dividing by zero.
  2. downtime_min > planned_min raises under --strict, warns under default.
  3. Negative units are rejected (warn under default, raise under strict).
  4. Missing required column in any of the three CSVs raises ValidationError
     with the column name in the message.
  5. Line-day key missing from floor but present in dashboard and raw is
     recorded as a coverage gap instead of being silently dropped.
  6. A valid happy-path row produces the expected canonical values within
     floating-point tolerance.
  7. Malformed numeric cell surfaces the row number and column name.
  8. Scrap rate with zero total units returns 0.0 (no divide-by-zero).
"""

from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from pathlib import Path

import artifact


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


RAW_FIELDNAMES = [
    "line_id", "day", "planned_min", "calendar_min", "scheduled_min",
    "downtime_min", "actual_units", "good_units", "scrapped_units",
    "ideal_rate_per_min",
]
SIDE_FIELDNAMES = ["line_id", "day", "oee", "scrap_rate", "throughput_per_hr"]


def _good_raw_row(**overrides) -> dict:
    row = {
        "line_id": "L01", "day": "2026-04-14",
        "planned_min": 960.0, "calendar_min": 1440.0, "scheduled_min": 1080.0,
        "downtime_min": 60.0, "actual_units": 2000.0,
        "good_units": 1940.0, "scrapped_units": 60.0,
        "ideal_rate_per_min": 2.4,
    }
    row.update(overrides)
    return row


def _good_side_row(**overrides) -> dict:
    row = {"line_id": "L01", "day": "2026-04-14",
           "oee": 0.75, "scrap_rate": 0.03, "throughput_per_hr": 129.0}
    row.update(overrides)
    return row


class CanonicalFormulaTests(unittest.TestCase):
    """Pure math on the canonical formulas. No I/O."""

    def test_planned_min_zero_returns_zero_oee(self):
        # planned_min == 0 must not divide by zero. Return 0.0 OEE.
        val = artifact.canonical_oee(
            planned_min=0.0, downtime_min=0.0,
            actual_units=100.0, ideal_rate_per_min=1.0, good_units=100.0,
        )
        self.assertEqual(val, 0.0)

    def test_scrap_rate_zero_total_returns_zero(self):
        self.assertEqual(artifact.canonical_scrap_rate(0.0, 0.0), 0.0)

    def test_throughput_zero_run_time_returns_zero(self):
        self.assertEqual(artifact.canonical_throughput(100.0, 0.0), 0.0)

    def test_happy_path_oee_matches_expected(self):
        # planned=960, downtime=60, run=900
        # availability = 900/960 = 0.9375
        # denom = 2.4 * 900 = 2160; performance = 2000/2160 ~= 0.9259 (capped <=1)
        # quality = 1940/2000 = 0.97
        # oee = 0.9375 * 0.9259259259 * 0.97 = approx 0.8420
        val = artifact.canonical_oee(
            planned_min=960.0, downtime_min=60.0,
            actual_units=2000.0, ideal_rate_per_min=2.4, good_units=1940.0,
        )
        self.assertAlmostEqual(val, 0.9375 * (2000 / 2160) * 0.97, places=6)

    def test_happy_path_scrap_and_throughput(self):
        self.assertAlmostEqual(
            artifact.canonical_scrap_rate(60.0, 2000.0), 0.03, places=6)
        # run=900 min = 15 hours; throughput = 1940 / 15 = 129.333...
        self.assertAlmostEqual(
            artifact.canonical_throughput(1940.0, 900.0), 1940 / 15, places=6)


class ValidationTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="reconcile_test_"))
        self.raw_path = self.tmp / "raw.csv"
        self.dash_path = self.tmp / "dash.csv"
        self.floor_path = self.tmp / "floor.csv"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_default(self, raw_rows=None, dash_rows=None, floor_rows=None):
        _write_csv(self.raw_path,
                   raw_rows or [_good_raw_row()],
                   RAW_FIELDNAMES)
        _write_csv(self.dash_path,
                   dash_rows or [_good_side_row()],
                   SIDE_FIELDNAMES)
        _write_csv(self.floor_path,
                   floor_rows or [_good_side_row()],
                   SIDE_FIELDNAMES)

    # 1. planned_min == 0: load_raw warns (permissive) and skips the row,
    #    so reconcile runs without crashing.
    def test_planned_min_zero_is_skipped_permissive(self):
        self._write_default(raw_rows=[_good_raw_row(planned_min=0.0)])
        payload = artifact.reconcile(
            csv_raw=self.raw_path,
            csv_dashboard=self.dash_path,
            csv_floor=self.floor_path,
            strict=False,
        )
        self.assertEqual(payload["validation"]["rows_accepted"], 0)
        self.assertEqual(payload["validation"]["rows_skipped"], 1)
        self.assertTrue(any("planned_min" in w for w in payload["validation"]["warnings"]))

    # 2. downtime_min > planned_min: permissive warns, strict raises.
    def test_downtime_exceeds_planned_permissive_warns(self):
        self._write_default(raw_rows=[_good_raw_row(downtime_min=2000.0)])
        payload = artifact.reconcile(
            csv_raw=self.raw_path,
            csv_dashboard=self.dash_path,
            csv_floor=self.floor_path,
            strict=False,
        )
        self.assertEqual(payload["validation"]["rows_skipped"], 1)
        self.assertTrue(any("downtime_min" in w for w in payload["validation"]["warnings"]))

    def test_downtime_exceeds_planned_strict_raises(self):
        self._write_default(raw_rows=[_good_raw_row(downtime_min=2000.0)])
        with self.assertRaises(artifact.ValidationError) as ctx:
            artifact.reconcile(
                csv_raw=self.raw_path,
                csv_dashboard=self.dash_path,
                csv_floor=self.floor_path,
                strict=True,
            )
        self.assertIn("downtime_min", str(ctx.exception))

    # 3. Negative units in input.
    def test_negative_units_strict_raises(self):
        self._write_default(raw_rows=[_good_raw_row(good_units=-10.0)])
        with self.assertRaises(artifact.ValidationError) as ctx:
            artifact.reconcile(
                csv_raw=self.raw_path,
                csv_dashboard=self.dash_path,
                csv_floor=self.floor_path,
                strict=True,
            )
        self.assertIn("good_units", str(ctx.exception))

    def test_negative_units_permissive_warns(self):
        self._write_default(raw_rows=[_good_raw_row(scrapped_units=-5.0)])
        payload = artifact.reconcile(
            csv_raw=self.raw_path,
            csv_dashboard=self.dash_path,
            csv_floor=self.floor_path,
            strict=False,
        )
        self.assertEqual(payload["validation"]["rows_skipped"], 1)
        self.assertTrue(any("scrapped_units" in w for w in payload["validation"]["warnings"]))

    # 4. Missing required column raises ValidationError naming the column.
    def test_missing_column_in_raw(self):
        bad_row = _good_raw_row()
        del bad_row["scrapped_units"]
        bad_fieldnames = [c for c in RAW_FIELDNAMES if c != "scrapped_units"]
        _write_csv(self.raw_path, [bad_row], bad_fieldnames)
        _write_csv(self.dash_path, [_good_side_row()], SIDE_FIELDNAMES)
        _write_csv(self.floor_path, [_good_side_row()], SIDE_FIELDNAMES)
        with self.assertRaises(artifact.ValidationError) as ctx:
            artifact.reconcile(
                csv_raw=self.raw_path,
                csv_dashboard=self.dash_path,
                csv_floor=self.floor_path,
            )
        self.assertIn("scrapped_units", str(ctx.exception))

    def test_missing_column_in_dashboard(self):
        bad_row = _good_side_row()
        del bad_row["throughput_per_hr"]
        bad_fieldnames = [c for c in SIDE_FIELDNAMES if c != "throughput_per_hr"]
        _write_csv(self.raw_path, [_good_raw_row()], RAW_FIELDNAMES)
        _write_csv(self.dash_path, [bad_row], bad_fieldnames)
        _write_csv(self.floor_path, [_good_side_row()], SIDE_FIELDNAMES)
        with self.assertRaises(artifact.ValidationError) as ctx:
            artifact.reconcile(
                csv_raw=self.raw_path,
                csv_dashboard=self.dash_path,
                csv_floor=self.floor_path,
            )
        self.assertIn("throughput_per_hr", str(ctx.exception))

    # 5. Missing line-day key in floor records a coverage gap.
    def test_missing_floor_key_records_coverage_gap(self):
        raw_rows = [_good_raw_row(day="2026-04-14"),
                    _good_raw_row(day="2026-04-15")]
        dash_rows = [_good_side_row(day="2026-04-14"),
                     _good_side_row(day="2026-04-15")]
        floor_rows = [_good_side_row(day="2026-04-14")]  # missing 04-15
        self._write_default(raw_rows=raw_rows, dash_rows=dash_rows, floor_rows=floor_rows)
        payload = artifact.reconcile(
            csv_raw=self.raw_path,
            csv_dashboard=self.dash_path,
            csv_floor=self.floor_path,
            strict=False,
        )
        gaps = payload["validation"]["coverage_gaps"]
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["missing_from"], "floor")
        self.assertEqual(gaps[0]["day"], "2026-04-15")

    # 6. Happy path: one valid row produces variance rows and no warnings.
    def test_happy_path_single_row(self):
        self._write_default()
        payload = artifact.reconcile(
            csv_raw=self.raw_path,
            csv_dashboard=self.dash_path,
            csv_floor=self.floor_path,
            strict=True,
        )
        self.assertEqual(payload["validation"]["rows_accepted"], 1)
        self.assertEqual(payload["validation"]["warnings"], [])
        self.assertEqual(len(payload["row_detail"]), 1)
        row = payload["row_detail"][0]
        self.assertAlmostEqual(row["scrap_canonical"], 0.03, places=4)

    # 7. Malformed numeric cell reports row number and column.
    def test_malformed_numeric_cell(self):
        bad = _good_raw_row()
        bad["planned_min"] = "not-a-number"
        _write_csv(self.raw_path, [bad], RAW_FIELDNAMES)
        _write_csv(self.dash_path, [_good_side_row()], SIDE_FIELDNAMES)
        _write_csv(self.floor_path, [_good_side_row()], SIDE_FIELDNAMES)
        with self.assertRaises(artifact.ValidationError) as ctx:
            artifact.reconcile(
                csv_raw=self.raw_path,
                csv_dashboard=self.dash_path,
                csv_floor=self.floor_path,
            )
        msg = str(ctx.exception)
        self.assertIn("planned_min", msg)
        self.assertIn("row 2", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
