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
