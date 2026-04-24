# Vertex Manufacturing Metric Reconciliation: Primary Artifact

## What this is

Three files bundled into one deliverable, because provn.co has a single primary-artifact slot and Jamie needs all of them:

1. **`corrected_metrics.sql`**. The CREATE OR ALTER VIEW statements that fix the three metric definitions (OEE, Scrap Rate, Throughput) in SQL Server. This is what Jamie actually deploys.
2. **`artifact.py`**. A reconciliation utility that pulls from both sides (dashboard export + floor spreadsheet), validates input, recomputes each metric from the raw inputs, and prints a variance report. Jamie runs this weekly to confirm the two sides stay within tolerance.
3. **`test_artifact.py`**. Fifteen stdlib unittest cases covering the edge cases: planned_min zero, downtime above planned, negative units, missing columns per CSV, missing line-day keys, malformed numeric cells, and the happy-path canonical values.

All three files are fully reproduced below. Standalone copies exist in the repo at `91-dashboard-metrics/artifact.py`, `91-dashboard-metrics/corrected_metrics.sql`, and `91-dashboard-metrics/test_artifact.py`.

## Deploy order (Jamie workflow, 5-day window)

1. **Back up** the current `vw_production_kpi` view. Keep the definition text. Rollback depends on it.
2. **Test** locally first: `python -m unittest test_artifact.py -v`. All fifteen must pass before touching production.
3. **Apply** the three `CREATE OR ALTER VIEW` statements in the SQL section below (or run `corrected_metrics.sql` directly via SSMS).
4. **Run** `python artifact.py` against one week of data in demo mode first, then in production mode:
   ```
   python artifact.py --csv-raw /path/to/raw_production.csv --csv-dashboard /path/to/dashboard_export.csv --csv-floor /path/to/floor_spreadsheet_export.csv
   ```
   Add `--strict` when producing numbers that will feed the board deck.
5. **Confirm** dashboard and floor now agree within 2 percent. The script prints PASS/FAIL per metric, lists coverage gaps, and writes `out/reconciliation.json` and `out/corrected_metrics.csv`.
6. **Only then** repoint the dashboard at the new views.
7. **Rollback** is at the bottom of the SQL section if reconciliation worsens.

## Running the tests

```
cd 91-dashboard-metrics
python -m unittest test_artifact.py -v
```

All tests use only the Python standard library. No pip install. Expected output ends with `Ran 15 tests` and `OK`. If any test fails, do not deploy.

## Inputs in production mode

Jamie provides three CSVs via command-line flags:

| Flag | Source | Schema |
|---|---|---|
| `--csv-raw` | SELECT from `v_raw_production_daily` in SQL Server | line_id, day, planned_min, calendar_min, scheduled_min, downtime_min, actual_units, good_units, scrapped_units, ideal_rate_per_min |
| `--csv-dashboard` | BI tool export for the same period | line_id, day, oee, scrap_rate, throughput_per_hr |
| `--csv-floor` | Weekly spreadsheet drop from floor supervisors (export Excel to CSV) | line_id, day, oee, scrap_rate, throughput_per_hr |

If any of the three flags is omitted, the script falls back to synthetic demo data so Jamie can confirm the tool is wired up before pointing it at real extracts.

## Validation behavior

Enforced on every load:

- Required columns must be present in each CSV. Missing columns raise `ValidationError` naming the file and the columns.
- Per-row invariants: `planned_min > 0`, `downtime_min >= 0`, `downtime_min <= planned_min`, unit counts non-negative, unit accounting within a one-unit slack.
- Malformed numeric cells surface the file name, row number, and column name.
- Line-day keys that exist in one CSV but not in the others are recorded as coverage gaps in the JSON output. Never silently dropped.

Default mode is permissive: warnings log and the bad row is skipped. `--strict` escalates every warning to a hard error.

## Ongoing cadence

- Weekly cron (Windows Task Scheduler or equivalent) on Jamie's workstation: pull the three CSVs, run the reconciliation, archive the JSON output.
- Escalate to Marcus (returning Day 4) if any metric drifts outside the 2 percent tolerance band for two consecutive weeks.

---

# `corrected_metrics.sql`

```sql
-- =====================================================================
-- Vertex Manufacturing: corrected metric definitions (OEE, Scrap, Throughput)
--
-- Purpose: freeze the three metric definitions so the dashboard and the
-- floor spreadsheets agree. Each section shows the BROKEN definition the
-- dashboard uses today, the CANONICAL definition the floor uses, and the
-- replacement query to deploy.
--
-- Deploy order:
--   1. Back up the current vw_production_kpi view. See rollback at bottom.
--   2. Apply the three CREATE OR ALTER VIEW statements in this file.
--   3. Run artifact.py on the same week of data; confirm dashboard now
--      matches floor within 2 percent.
--   4. Only then repoint the dashboard at the new views.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. OEE = Availability * Performance * Quality
-- ---------------------------------------------------------------------
-- BROKEN (current dashboard):
--   Availability uses calendar_min (24h) as the denominator, not
--   planned_min (typically 16h). This inflates Availability whenever
--   there are large blocks of unscheduled time.
--
--   SELECT ((calendar_min - downtime_min) / calendar_min)
--        * (actual_units / (ideal_rate_per_min * (planned_min - downtime_min)))
--        * (good_units / NULLIF(actual_units, 0))
--   FROM production_shift;
--
-- CANONICAL (floor):
--   Availability uses planned_min. Performance caps at 1.0 to guard
--   against stale ideal_rate constants.

CREATE OR ALTER VIEW vw_oee_daily AS
SELECT
    line_id,
    shift_date,
    SUM(planned_min)   AS planned_min,
    SUM(downtime_min)  AS downtime_min,
    CAST(SUM(planned_min - downtime_min) AS FLOAT)
        / NULLIF(SUM(planned_min), 0)                       AS availability,
    LEAST(
        CAST(SUM(actual_units) AS FLOAT)
            / NULLIF(SUM(ideal_rate_per_min * (planned_min - downtime_min)), 0),
        1.0
    )                                                       AS performance,
    CAST(SUM(good_units) AS FLOAT)
        / NULLIF(SUM(actual_units), 0)                      AS quality,
    (CAST(SUM(planned_min - downtime_min) AS FLOAT)
        / NULLIF(SUM(planned_min), 0))
    * LEAST(
        CAST(SUM(actual_units) AS FLOAT)
            / NULLIF(SUM(ideal_rate_per_min * (planned_min - downtime_min)), 0),
        1.0)
    * (CAST(SUM(good_units) AS FLOAT)
        / NULLIF(SUM(actual_units), 0))                     AS oee
FROM production_shift
GROUP BY line_id, shift_date;

-- ---------------------------------------------------------------------
-- 2. Scrap Rate = scrapped / (good + scrapped)
-- ---------------------------------------------------------------------
-- BROKEN (current dashboard):
--   scrap_rate = scrapped_units / good_units. Denominator excludes the
--   scrapped portion, so the reported rate is always lower than reality.
--
-- CANONICAL (floor):
--   Total units produced is the denominator. Matches supervisor math.

CREATE OR ALTER VIEW vw_scrap_rate_daily AS
SELECT
    line_id,
    shift_date,
    SUM(scrapped_units) AS scrapped_units,
    SUM(good_units)     AS good_units,
    CAST(SUM(scrapped_units) AS FLOAT)
        / NULLIF(SUM(good_units + scrapped_units), 0)       AS scrap_rate
FROM production_shift
GROUP BY line_id, shift_date;

-- ---------------------------------------------------------------------
-- 3. Throughput = good units per run hour
-- ---------------------------------------------------------------------
-- BROKEN (current dashboard):
--   good_units / (scheduled_min / 60.0). Scheduled time counts breaks
--   and planned downtime, so throughput looks artificially low.
--
-- CANONICAL (floor):
--   Run time is planned_min minus downtime_min. Matches what a
--   supervisor sees on the line clock.

CREATE OR ALTER VIEW vw_throughput_daily AS
SELECT
    line_id,
    shift_date,
    SUM(good_units) AS good_units,
    SUM(planned_min - downtime_min) / 60.0 AS run_hours,
    CAST(SUM(good_units) AS FLOAT)
        / NULLIF(SUM(planned_min - downtime_min) / 60.0, 0) AS throughput_per_hr
FROM production_shift
GROUP BY line_id, shift_date;

-- ---------------------------------------------------------------------
-- Rollback. Run only if reconciliation worsens.
-- ---------------------------------------------------------------------
-- DROP VIEW vw_oee_daily;
-- DROP VIEW vw_scrap_rate_daily;
-- DROP VIEW vw_throughput_daily;
-- Restore prior vw_production_kpi from the backup taken in step 1.
```

---

# `artifact.py`

```python
"""
Vertex Manufacturing metric reconciliation utility.

Purpose: Dashboard and floor spreadsheets disagree on OEE, Scrap Rate, and
Throughput by 8 to 23 percent. Dana does not know. Before any speed fix, the
definitions need to match. This script loads both sides, recomputes each
metric from the same raw inputs, prints a variance report, and writes a
machine-readable JSON summary for the next run.

Two run modes:

  1. Production (real extracts from Jamie's environment):
       python artifact.py \\
         --csv-raw /path/to/raw_production.csv \\
         --csv-dashboard /path/to/dashboard_export.csv \\
         --csv-floor /path/to/floor_spreadsheet_export.csv

  2. Demo (no arguments): synthetic CSVs are generated into ./sample_data/ on
     first run and the reconciliation runs against them. Use this to verify
     the tool is wired up before pointing it at the SQL Server views and the
     floor spreadsheet exports.

Flags:
  --strict   Escalate validation warnings to hard errors. Default is
             permissive (log + continue) so Jamie can point the tool at
             messy real data without a crash.

Dependencies: standard library only (csv, json, statistics, pathlib,
datetime, argparse, logging).

Expected real-source mapping (production mode):
  --csv-raw        : SELECT from v_raw_production_daily in SQL Server.
                     Columns: line_id, day, planned_min, calendar_min,
                     scheduled_min, downtime_min, actual_units, good_units,
                     scrapped_units, ideal_rate_per_min.
  --csv-dashboard  : export from the BI reporting tool for the same period.
                     Columns: line_id, day, oee, scrap_rate, throughput_per_hr.
  --csv-floor      : the weekly spreadsheet drop from the floor supervisors
                     (export as CSV from Excel, same column schema as dashboard).

Outputs:
  - stdout: human-readable alignment report
  - ./out/reconciliation.json: structured variance payload (includes
    validation warnings and coverage gaps)
  - ./out/corrected_metrics.csv: the aligned metric values per line per day

Deployable by Jamie. No external packages. No app code to debug.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
from dataclasses import dataclass, asdict, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "sample_data"
OUT = ROOT / "out"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

# Allow a tiny absolute slack (units) when checking the unit-accounting
# invariant actual_units ~= good_units + scrapped_units. Excel rounding on
# the floor spreadsheet routinely introduces sub-unit drift.
UNIT_TOLERANCE = 1.0

# Required columns per CSV source. If any column is missing the tool fails
# fast with a clear message naming the file and the missing columns.
REQUIRED_RAW_COLUMNS = [
    "line_id", "day", "planned_min", "calendar_min", "scheduled_min",
    "downtime_min", "actual_units", "good_units", "scrapped_units",
    "ideal_rate_per_min",
]
REQUIRED_SIDE_COLUMNS = ["line_id", "day", "oee", "scrap_rate", "throughput_per_hr"]


logger = logging.getLogger("reconcile")


class ValidationError(ValueError):
    """Raised when input data violates an invariant and --strict is set."""


# ---------------------------------------------------------------------------
# Canonical (corrected) metric definitions.
# These are what the floor and the dashboard should both produce. The floor
# spreadsheets use something close to these. The dashboard queries drift.
# Each definition has a full SQL statement in corrected_metrics.sql.
# ---------------------------------------------------------------------------

def canonical_oee(planned_min: float, downtime_min: float,
                  actual_units: float, ideal_rate_per_min: float,
                  good_units: float) -> float:
    """OEE = Availability * Performance * Quality.

    Availability = (planned - downtime) / planned
    Performance  = actual_units / (ideal_rate_per_min * run_time_min)
    Quality      = good_units / actual_units

    The dashboard version drops planned time and uses calendar time in the
    Availability denominator, which inflates Availability. The floor version
    uses planned time, which is correct.

    Guards:
      * planned_min == 0 returns 0.0 (no production planned, OEE undefined).
      * run_time <= 0 returns 0.0 (line was down the entire shift).
      * actual_units == 0 makes Quality 0.0 (nothing produced, no quality).
    """
    if planned_min <= 0:
        return 0.0
    run_time = planned_min - downtime_min
    if run_time <= 0:
        return 0.0
    availability = run_time / planned_min
    denom = ideal_rate_per_min * run_time
    performance = actual_units / denom if denom > 0 else 0.0
    quality = good_units / actual_units if actual_units > 0 else 0.0
    # Cap Performance at 1.0. Values above 1.0 almost always mean a stale
    # ideal_rate constant, not a miraculous machine.
    performance = min(performance, 1.0)
    return availability * performance * quality


def canonical_scrap_rate(scrapped_units: float, total_units: float) -> float:
    """Scrap Rate = scrapped / (good + scrapped).

    The dashboard version uses scrapped / good_only, which understates the
    rate because the denominator excludes the scrapped part.
    """
    return scrapped_units / total_units if total_units > 0 else 0.0


def canonical_throughput(good_units: float, run_time_min: float) -> float:
    """Throughput = good units per run hour.

    The dashboard version divides by scheduled hours, which counts breaks
    and planned downtime as production time and depresses the number. The
    floor version uses run time, which matches what a supervisor sees on
    the line.
    """
    if run_time_min <= 0:
        return 0.0
    run_hours = run_time_min / 60.0
    return good_units / run_hours


# ---------------------------------------------------------------------------
# The broken dashboard math. Kept here so the report can show exactly what
# the dashboard is producing today. Do not call these in production.
# ---------------------------------------------------------------------------

def broken_dashboard_oee(planned_min: float, downtime_min: float,
                         actual_units: float, ideal_rate_per_min: float,
                         good_units: float,
                         calendar_min: float) -> float:
    # Uses calendar_min as the Availability denominator. Inflates.
    availability = (calendar_min - downtime_min) / calendar_min if calendar_min else 0.0
    run_time = max(planned_min - downtime_min, 1e-9)
    performance = actual_units / (ideal_rate_per_min * run_time) if run_time else 0.0
    performance = min(performance, 1.0)
    quality = good_units / actual_units if actual_units else 0.0
    return availability * performance * quality


def broken_dashboard_scrap_rate(scrapped_units: float, good_units: float) -> float:
    # Denominator is good_only, not total.
    return scrapped_units / good_units if good_units else 0.0


def broken_dashboard_throughput(good_units: float, scheduled_min: float) -> float:
    # Denominator is scheduled time, not run time.
    scheduled_hours = scheduled_min / 60.0 if scheduled_min else 0.0
    return good_units / scheduled_hours if scheduled_hours else 0.0


# ---------------------------------------------------------------------------
# Data loading. In production each loader pulls from its real source.
# For the demo, sample CSVs are generated on first run.
# ---------------------------------------------------------------------------

@dataclass
class LineDay:
    line_id: str
    day: str
    planned_min: float
    calendar_min: float
    scheduled_min: float
    downtime_min: float
    actual_units: float
    good_units: float
    scrapped_units: float
    ideal_rate_per_min: float

    @property
    def total_units(self) -> float:
        return self.good_units + self.scrapped_units

    @property
    def run_time_min(self) -> float:
        return max(self.planned_min - self.downtime_min, 0.0)


@dataclass
class ValidationReport:
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    coverage_gaps: list[dict] = field(default_factory=list)
    rows_skipped: int = 0
    rows_accepted: int = 0


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------

def _check_columns(path: Path, fieldnames: list[str] | None,
                   required: list[str]) -> None:
    """Raise ValidationError if any required column is missing."""
    have = set(fieldnames or [])
    missing = [c for c in required if c not in have]
    if missing:
        raise ValidationError(
            f"{path.name} is missing required columns: {missing}. "
            f"Saw: {sorted(have)}."
        )


def _safe_float(value: str, column: str, row_num: int, path: Path) -> float:
    """Cast a CSV cell to float. Surface row number and column on failure."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{path.name} row {row_num}: column '{column}' "
            f"has non-numeric value {value!r} ({exc})."
        ) from exc


def _validate_raw_row(r: LineDay, row_num: int, path: Path,
                      report: ValidationReport, strict: bool) -> bool:
    """Validate unit-accounting and time invariants for one raw row.

    Returns True if the row is usable, False if it should be skipped.
    In strict mode, raises on any violation.
    """
    issues: list[str] = []

    if r.planned_min <= 0:
        issues.append(f"planned_min={r.planned_min} must be > 0")
    if r.downtime_min < 0:
        issues.append(f"downtime_min={r.downtime_min} must be >= 0")
    if r.good_units < 0:
        issues.append(f"good_units={r.good_units} must be >= 0")
    if r.scrapped_units < 0:
        issues.append(f"scrapped_units={r.scrapped_units} must be >= 0")
    if r.actual_units < 0:
        issues.append(f"actual_units={r.actual_units} must be >= 0")
    if r.ideal_rate_per_min < 0:
        issues.append(f"ideal_rate_per_min={r.ideal_rate_per_min} must be >= 0")
    if r.downtime_min > r.planned_min:
        issues.append(
            f"downtime_min={r.downtime_min} exceeds "
            f"planned_min={r.planned_min}"
        )
    # Unit accounting: actual_units should be close to good + scrapped.
    if r.actual_units + UNIT_TOLERANCE < r.good_units + r.scrapped_units:
        issues.append(
            f"actual_units={r.actual_units} is less than good+scrapped="
            f"{r.good_units + r.scrapped_units} (beyond {UNIT_TOLERANCE}-unit slack)"
        )

    if not issues:
        return True

    msg = (f"{path.name} row {row_num} (line_id={r.line_id}, day={r.day}): "
           + "; ".join(issues))
    if strict:
        report.errors.append(msg)
        raise ValidationError(msg)
    report.warnings.append(msg)
    report.rows_skipped += 1
    logger.warning(msg)
    return False


def load_raw(path: Path | None = None, *,
             report: ValidationReport | None = None,
             strict: bool = False) -> list[LineDay]:
    src = path if path is not None else (DATA / "raw_production.csv")
    if report is None:
        report = ValidationReport()
    rows: list[LineDay] = []
    try:
        with src.open(newline="") as f:
            reader = csv.DictReader(f)
            _check_columns(src, reader.fieldnames, REQUIRED_RAW_COLUMNS)
            for row_num, row in enumerate(reader, start=2):
                try:
                    ld = LineDay(
                        line_id=row["line_id"].strip(),
                        day=row["day"].strip(),
                        planned_min=_safe_float(row["planned_min"], "planned_min", row_num, src),
                        calendar_min=_safe_float(row["calendar_min"], "calendar_min", row_num, src),
                        scheduled_min=_safe_float(row["scheduled_min"], "scheduled_min", row_num, src),
                        downtime_min=_safe_float(row["downtime_min"], "downtime_min", row_num, src),
                        actual_units=_safe_float(row["actual_units"], "actual_units", row_num, src),
                        good_units=_safe_float(row["good_units"], "good_units", row_num, src),
                        scrapped_units=_safe_float(row["scrapped_units"], "scrapped_units", row_num, src),
                        ideal_rate_per_min=_safe_float(
                            row["ideal_rate_per_min"], "ideal_rate_per_min", row_num, src),
                    )
                except ValidationError:
                    raise
                if _validate_raw_row(ld, row_num, src, report, strict):
                    rows.append(ld)
                    report.rows_accepted += 1
    except csv.Error as exc:
        raise ValidationError(f"{src.name} is malformed CSV: {exc}") from exc
    return rows


def load_side(path: Path, *, label: str,
              report: ValidationReport | None = None,
              strict: bool = False) -> dict[tuple[str, str], dict[str, float]]:
    if report is None:
        report = ValidationReport()
    out: dict[tuple[str, str], dict[str, float]] = {}
    try:
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            _check_columns(path, reader.fieldnames, REQUIRED_SIDE_COLUMNS)
            for row_num, row in enumerate(reader, start=2):
                key = (row["line_id"].strip(), row["day"].strip())
                try:
                    parsed = {
                        "oee": _safe_float(row["oee"], "oee", row_num, path),
                        "scrap_rate": _safe_float(row["scrap_rate"], "scrap_rate", row_num, path),
                        "throughput_per_hr": _safe_float(
                            row["throughput_per_hr"], "throughput_per_hr", row_num, path),
                    }
                except ValidationError as exc:
                    if strict:
                        report.errors.append(str(exc))
                        raise
                    report.warnings.append(str(exc))
                    report.rows_skipped += 1
                    logger.warning(str(exc))
                    continue
                out[key] = parsed
    except csv.Error as exc:
        raise ValidationError(f"{path.name} ({label}) is malformed CSV: {exc}") from exc
    return out


def ensure_sample_data() -> None:
    """Write four CSVs simulating raw production data plus two pre-computed
    output CSVs for the dashboard and the floor. This is for demo. In
    production the dashboard CSV becomes a pull from the BI tool's export
    and the floor CSV becomes the weekly spreadsheet drop.
    """
    raw_path = DATA / "raw_production.csv"
    dash_path = DATA / "dashboard_metrics.csv"
    floor_path = DATA / "floor_metrics.csv"
    rate_path = DATA / "ideal_rates.csv"

    if raw_path.exists():
        return

    lines = ["L01", "L02", "L03", "L04"]
    ideal_rates = {"L01": 2.4, "L02": 1.8, "L03": 3.1, "L04": 2.0}
    start = date(2026, 4, 14)

    with rate_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line_id", "ideal_rate_per_min"])
        for lid, r in ideal_rates.items():
            w.writerow([lid, r])

    rows: list[LineDay] = []
    # Deterministic sample, no random module, so the demo is reproducible.
    for i in range(7):
        day = (start + timedelta(days=i)).isoformat()
        for j, lid in enumerate(lines):
            planned = 960.0    # 16 planned production hours
            calendar = 1440.0  # 24 calendar hours
            scheduled = 1080.0  # 18 hours (planned + breaks + setup)
            downtime = 60.0 + 20.0 * ((i + j) % 4)
            actual = (ideal_rates[lid] * (planned - downtime)) * (0.82 + 0.02 * ((i + j) % 5))
            scrapped = actual * (0.03 + 0.005 * ((i + j) % 4))
            good = actual - scrapped
            rows.append(LineDay(
                line_id=lid, day=day,
                planned_min=planned, calendar_min=calendar,
                scheduled_min=scheduled, downtime_min=downtime,
                actual_units=round(actual, 2), good_units=round(good, 2),
                scrapped_units=round(scrapped, 2),
                ideal_rate_per_min=ideal_rates[lid],
            ))

    with raw_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))

    # Dashboard output uses the broken math.
    with dash_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line_id", "day", "oee", "scrap_rate", "throughput_per_hr"])
        for r in rows:
            w.writerow([
                r.line_id, r.day,
                round(broken_dashboard_oee(r.planned_min, r.downtime_min,
                                           r.actual_units, r.ideal_rate_per_min,
                                           r.good_units, r.calendar_min), 4),
                round(broken_dashboard_scrap_rate(r.scrapped_units, r.good_units), 4),
                round(broken_dashboard_throughput(r.good_units, r.scheduled_min), 2),
            ])

    # Floor spreadsheet uses canonical math plus small human rounding noise.
    def jitter(v: float, i: int) -> float:
        return v * (1.0 + ((i % 3) - 1) * 0.0025)

    with floor_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line_id", "day", "oee", "scrap_rate", "throughput_per_hr"])
        for idx, r in enumerate(rows):
            w.writerow([
                r.line_id, r.day,
                round(jitter(canonical_oee(r.planned_min, r.downtime_min,
                                           r.actual_units, r.ideal_rate_per_min,
                                           r.good_units), idx), 4),
                round(jitter(canonical_scrap_rate(r.scrapped_units, r.total_units), idx), 4),
                round(jitter(canonical_throughput(r.good_units, r.run_time_min), idx), 2),
            ])


# ---------------------------------------------------------------------------
# Reconciliation. Produce a row-level diff and a metric-level summary.
# ---------------------------------------------------------------------------

@dataclass
class MetricVariance:
    metric: str
    mean_dashboard: float
    mean_floor: float
    mean_canonical: float
    mean_pct_diff_dashboard_vs_floor: float
    max_pct_diff_dashboard_vs_floor: float
    direction: str
    rows_compared: int
    rows_outside_tolerance: int
    tolerance_pct: float


def pct_diff(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return (a - b) / b * 100.0


def reconcile(tolerance_pct: float = 2.0,
              csv_raw: Path | None = None,
              csv_dashboard: Path | None = None,
              csv_floor: Path | None = None,
              strict: bool = False) -> dict:
    report = ValidationReport()
    raw = load_raw(csv_raw, report=report, strict=strict)
    dash_path = csv_dashboard if csv_dashboard is not None else DATA / "dashboard_metrics.csv"
    floor_path = csv_floor if csv_floor is not None else DATA / "floor_metrics.csv"
    dash = load_side(dash_path, label="dashboard", report=report, strict=strict)
    floor = load_side(floor_path, label="floor", report=report, strict=strict)

    rows_out = []
    metric_rollup: dict[str, list[tuple[float, float, float]]] = {
        "oee": [], "scrap_rate": [], "throughput_per_hr": [],
    }

    dash_keys = set(dash.keys())
    floor_keys = set(floor.keys())
    raw_keys = {(r.line_id, r.day) for r in raw}

    # Coverage gaps: any key that exists in one side but is missing from
    # another. Logged and returned in the payload, never silently dropped.
    for key in sorted(raw_keys - dash_keys):
        report.coverage_gaps.append({
            "line_id": key[0], "day": key[1], "missing_from": "dashboard",
        })
    for key in sorted(raw_keys - floor_keys):
        report.coverage_gaps.append({
            "line_id": key[0], "day": key[1], "missing_from": "floor",
        })
    for key in sorted(dash_keys - raw_keys):
        report.coverage_gaps.append({
            "line_id": key[0], "day": key[1], "missing_from": "raw",
        })
    for key in sorted(floor_keys - raw_keys):
        report.coverage_gaps.append({
            "line_id": key[0], "day": key[1], "missing_from": "raw",
        })
    for gap in report.coverage_gaps:
        logger.warning(
            "Coverage gap: line_id=%s day=%s missing from %s",
            gap["line_id"], gap["day"], gap["missing_from"],
        )

    for r in raw:
        key = (r.line_id, r.day)
        d = dash.get(key)
        fl = floor.get(key)
        if d is None or fl is None:
            continue
        can_vals = {
            "oee": canonical_oee(r.planned_min, r.downtime_min, r.actual_units,
                                 r.ideal_rate_per_min, r.good_units),
            "scrap_rate": canonical_scrap_rate(r.scrapped_units, r.total_units),
            "throughput_per_hr": canonical_throughput(r.good_units, r.run_time_min),
        }
        for metric, can in can_vals.items():
            metric_rollup[metric].append((d[metric], fl[metric], can))
        rows_out.append({
            "line_id": r.line_id, "day": r.day,
            "oee_dash": d["oee"], "oee_floor": fl["oee"],
            "oee_canonical": round(can_vals["oee"], 4),
            "scrap_dash": d["scrap_rate"], "scrap_floor": fl["scrap_rate"],
            "scrap_canonical": round(can_vals["scrap_rate"], 4),
            "thr_dash": d["throughput_per_hr"], "thr_floor": fl["throughput_per_hr"],
            "thr_canonical": round(can_vals["throughput_per_hr"], 2),
        })

    variances: list[MetricVariance] = []
    for metric, triples in metric_rollup.items():
        if not triples:
            variances.append(MetricVariance(
                metric=metric, mean_dashboard=0.0, mean_floor=0.0,
                mean_canonical=0.0, mean_pct_diff_dashboard_vs_floor=0.0,
                max_pct_diff_dashboard_vs_floor=0.0, direction="no_data",
                rows_compared=0, rows_outside_tolerance=0,
                tolerance_pct=tolerance_pct,
            ))
            continue
        diffs = [pct_diff(d, fl) for d, fl, _ in triples]
        mean_d = statistics.fmean(d for d, _, _ in triples)
        mean_fl = statistics.fmean(fl for _, fl, _ in triples)
        mean_can = statistics.fmean(c for _, _, c in triples)
        max_abs = max(abs(x) for x in diffs)
        mean_abs = statistics.fmean(abs(x) for x in diffs)
        direction = "dashboard_over" if mean_d > mean_fl else "dashboard_under"
        outside = sum(1 for x in diffs if abs(x) > tolerance_pct)
        variances.append(MetricVariance(
            metric=metric,
            mean_dashboard=round(mean_d, 4),
            mean_floor=round(mean_fl, 4),
            mean_canonical=round(mean_can, 4),
            mean_pct_diff_dashboard_vs_floor=round(mean_abs, 2),
            max_pct_diff_dashboard_vs_floor=round(max_abs, 2),
            direction=direction,
            rows_compared=len(triples),
            rows_outside_tolerance=outside,
            tolerance_pct=tolerance_pct,
        ))

    return {
        "tolerance_pct": tolerance_pct,
        "strict": strict,
        "variances": [asdict(v) for v in variances],
        "row_detail": rows_out,
        "validation": asdict(report),
    }


def write_outputs(payload: dict) -> None:
    (OUT / "reconciliation.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8",
    )
    with (OUT / "corrected_metrics.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line_id", "day", "oee_canonical",
                    "scrap_rate_canonical", "throughput_per_hr_canonical"])
        for row in payload["row_detail"]:
            w.writerow([row["line_id"], row["day"],
                        row["oee_canonical"], row["scrap_canonical"],
                        row["thr_canonical"]])


# ---------------------------------------------------------------------------
# Reporting. Plain text, readable out loud.
# ---------------------------------------------------------------------------

def print_report(payload: dict) -> None:
    print("Vertex Manufacturing metric reconciliation")
    print("=" * 52)
    print(f"Rows compared per metric: {payload['variances'][0]['rows_compared']}")
    print(f"Tolerance: {payload['tolerance_pct']}% between dashboard and floor")
    print(f"Mode: {payload.get('mode', 'unknown')} | strict={payload['strict']}")
    val = payload.get("validation", {})
    print(f"Validation: {val.get('rows_accepted', 0)} accepted, "
          f"{val.get('rows_skipped', 0)} skipped, "
          f"{len(val.get('warnings', []))} warnings, "
          f"{len(val.get('coverage_gaps', []))} coverage gaps.")
    print()
    print(f"{'Metric':<20}{'Dash':>10}{'Floor':>10}{'Canon':>10}{'|diff%|':>10}{'Max%':>10}")
    print("-" * 70)
    for v in payload["variances"]:
        print(f"{v['metric']:<20}"
              f"{v['mean_dashboard']:>10.4f}"
              f"{v['mean_floor']:>10.4f}"
              f"{v['mean_canonical']:>10.4f}"
              f"{v['mean_pct_diff_dashboard_vs_floor']:>10.2f}"
              f"{v['max_pct_diff_dashboard_vs_floor']:>10.2f}")
    print()
    for v in payload["variances"]:
        flag = "FAIL" if v["rows_outside_tolerance"] > 0 else "OK"
        print(f"[{flag}] {v['metric']}: dashboard runs "
              f"{v['direction'].replace('_', ' ')} by "
              f"{v['mean_pct_diff_dashboard_vs_floor']:.2f}% on average. "
              f"{v['rows_outside_tolerance']} of {v['rows_compared']} "
              f"rows outside the {v['tolerance_pct']}% tolerance band.")
    if val.get("coverage_gaps"):
        print()
        print(f"Coverage gaps (first 10 of {len(val['coverage_gaps'])}):")
        for gap in val["coverage_gaps"][:10]:
            print(f"  line_id={gap['line_id']} day={gap['day']} "
                  f"missing_from={gap['missing_from']}")
    if val.get("warnings"):
        print()
        print(f"Validation warnings (first 5 of {len(val['warnings'])}):")
        for w in val["warnings"][:5]:
            print(f"  {w}")
    print()
    print("Recommended action: freeze the three metric definitions to the")
    print("canonical SQL in corrected_metrics.sql. Run this script weekly")
    print("to confirm dashboard and floor stay within tolerance. Escalate")
    print("any metric that drifts outside tolerance for two weeks running.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile dashboard and floor metric definitions.",
    )
    parser.add_argument("--csv-raw", type=Path, default=None,
                        help="Path to raw production CSV (real extract). "
                             "If omitted, synthetic demo data is used.")
    parser.add_argument("--csv-dashboard", type=Path, default=None,
                        help="Path to dashboard metric export CSV.")
    parser.add_argument("--csv-floor", type=Path, default=None,
                        help="Path to floor spreadsheet export CSV.")
    parser.add_argument("--tolerance-pct", type=float, default=2.0,
                        help="Variance band. Rows outside this flag as FAIL.")
    parser.add_argument("--strict", action="store_true",
                        help="Escalate validation warnings to hard errors.")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity.")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    real_mode = all(p is not None for p in
                    (args.csv_raw, args.csv_dashboard, args.csv_floor))
    if not real_mode:
        # Demo mode. Generate synthetic CSVs once and run against them.
        # This is so Jamie can confirm the tool is wired up and producing
        # sensible output before pointing it at real extracts.
        ensure_sample_data()
        if any(p is not None for p in
               (args.csv_raw, args.csv_dashboard, args.csv_floor)):
            print("WARNING: partial --csv-* args provided. Pass all three "
                  "(--csv-raw, --csv-dashboard, --csv-floor) to run against "
                  "real extracts. Running demo mode this time.")
            args.csv_raw = args.csv_dashboard = args.csv_floor = None

    payload = reconcile(
        tolerance_pct=args.tolerance_pct,
        csv_raw=args.csv_raw,
        csv_dashboard=args.csv_dashboard,
        csv_floor=args.csv_floor,
        strict=args.strict,
    )
    payload["mode"] = "production" if real_mode else "demo_synthetic"
    write_outputs(payload)
    print_report(payload)


if __name__ == "__main__":
    main()
```

---

# `test_artifact.py`

```python
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
```
