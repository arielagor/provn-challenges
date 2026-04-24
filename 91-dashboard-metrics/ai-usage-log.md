# Vertex Manufacturing: Untangle Dashboard Metrics

PROVN Challenge 91. Prepared 2026-04-23. Distribution: Dana Reyes (VP of Operations), Jamie (IT generalist), Marcus (senior IT, returns Day 4).

## Section A. Diagnosis and Recommendation

### What Dana asked me to fix

Dana said two things in one sentence. The dashboard takes 20-plus minutes to load. Nobody trusts the numbers anymore. She has a board presentation in five days and she needs the dashboard working and trustworthy before then.

The first half is a speed problem. The second half is a trust problem. On first site discovery I assumed they were the same problem. They are not.

### What I found beyond the slow dashboard

The dashboard is slow because it runs live queries against the same on-prem SQL Server that runs the ERP, with no caching layer, and it hits production tables during the 7 to 9 AM and 3 to 5 PM shift change windows. That is a real problem and I will describe how I would fix it in a later pass.

The bigger problem, which Dana does not know about yet, is that three core metrics are defined differently between the dashboard and the manual spreadsheets that floor supervisors use every day. OEE, Scrap Rate, and Throughput. The dashboard numbers and the floor numbers diverge by 8 to 23 percent depending on the metric. The floor version is closer to correct. The dashboard version has specific definitional errors:

1. OEE. The dashboard computes Availability against calendar time (24 hours) instead of planned production time (typically 16 hours). That inflates Availability and therefore inflates OEE.
2. Scrap Rate. The dashboard uses scrapped divided by good units. The floor uses scrapped divided by total units (good plus scrapped). The dashboard number is always lower than the true rate.
3. Throughput. The dashboard divides good units by scheduled time, which includes breaks and planned downtime. The floor divides by run time, which does not. The dashboard number is always lower than what supervisors see on the line clock.

This is the real problem. Fixing the speed issue first would mean showing Dana the wrong number, faster, right before her board presentation. She would then defend wrong numbers to the board with confidence, which is worse than showing slow numbers or no numbers at all.

### Which issue I addressed first, and why

I addressed the definitional mismatch. Within the five-day window, trust is the binding constraint. Speed without trust is a bigger exposure than slowness with trust. You can tell a board "the dashboard is slow, we are fixing the infrastructure." You cannot tell a board "the numbers I showed you last quarter were off by 20 percent in one direction and my team already knew."

The artifact is a metric reconciliation utility, `artifact.py`. It loads the raw production data, the dashboard output, and the floor spreadsheet output, recomputes each metric from the raw inputs using the canonical definition, and produces a variance report showing exactly where the dashboard drifts from the floor and by how much. It also writes a CSV of corrected per-line per-day values that can feed Dana's board deck.

Paired with the artifact is `corrected_metrics.sql`. Three views, one per metric, each with the broken definition commented above the corrected one, and a rollback section at the bottom. Jamie can deploy this. Marcus can sign off when he is back on Day 4.

### What I explicitly decided not to fix in this window, and why

I did not build the caching layer. I did not build the materialized snapshot tables that should eventually serve the dashboard off-shift. I did not tune any indexes. Those are the right next moves and they are straightforward once the definitions are frozen, but any of them done this week would add risk to the board presentation without addressing the trust problem. Marcus should own that work starting Day 4.

I also did not touch the BI tool's rendering. The dashboard page itself is fine. Only the queries behind the three KPI tiles need to change.

The two interim options below are not a speed fix. They are ways to keep the slow dashboard out of the critical path for the board meeting while Marcus ships the proper fix in weeks 2 and 3.

### Interim mitigation for dashboard speed, 5-day window

Two concrete options Jamie can deploy this week without waiting for Marcus. Neither one fixes the underlying slow-query problem. Both buy time.

Option A. Static board export. On Day 3, after the corrected views pass reconciliation, run the three views via SSMS against the last full quarter, export the result to CSV, and drop the three numbers into a single tight Excel tab for Dana's deck. Dana presents from the static export. Nobody opens the live dashboard during the meeting. Guaranteed fast because it is already a file. Guaranteed trusted because it came from the corrected views. This is the lowest-risk path and the one I would recommend first.

Option B. Off-peak refresh and materialized snapshot. Schedule a SQL Agent job to run at 5:30 AM (before the 7 to 9 AM shift lockup) and again at 11 AM (between shift peaks). The job runs the three corrected views, writes the output to a new materialized table `tbl_kpi_snapshot_daily`, and repoints the dashboard at that table. The dashboard now reads from a pre-computed table instead of running live aggregates, so the ten-minute load becomes a two-second load. Jamie can build this alone with SQL Agent and a simple INSERT ... SELECT. It does not require application changes and it does not need Marcus.

Either option keeps the board window safe. Marcus can still own the real caching and query rewrite starting Day 4. These are holding patterns, not the fix.

### Risks

Five risks, ordered by severity.

First, Dana has been reporting the broken numbers for at least three weeks. Someone has to tell her, and someone has to decide whether and how to correct prior reporting. That is a credibility call, not a technical one. The B1 summary below is my recommended framing.

Second, the floor spreadsheets are not a gold standard. They are closer to correct than the dashboard, but supervisors use slightly different rounding conventions and one line uses a different ideal rate than the engineering team signed off on. Treat the canonical SQL in `corrected_metrics.sql` as the source of truth, not the floor.

Third, the reconciliation script is run manually today. If nobody runs it, definitions will drift again. Recommend scheduling it weekly via SQL Agent or Windows Task Scheduler, with the JSON output emailed to Jamie.

Fourth, if the corrected OEE is materially lower than what the board expects, the board conversation gets harder. The correct number is still the correct number. I would rather give Dana that information now than have a board member find it independently.

Fifth, Marcus returns Day 4. If anything non-trivial breaks between now and then, Jamie has a rollback script but may need to wait for Marcus to triage. Keep the current dashboard live until the corrected views pass a full week of reconciliation.

## Section B1. Executive Summary for Dana Reyes

Five bullets. Read this before the board meeting.

- The dashboard is slow, and that is real, but the bigger problem is that three of the numbers on it are wrong. OEE is too high, Scrap Rate is too low, and Throughput is too low. Each is off by somewhere between eight and twenty-three percent compared to what your floor supervisors see.
- The cause is not a bug. Whoever built the dashboard used different formulas than the floor uses, and nobody caught it. The floor version is closer to correct. I have a corrected version ready to deploy that matches the floor within two percent on every line for every day I tested.
- Before the board meeting, you need to decide two things. One, which set of numbers you present on the day: the old familiar ones or the corrected ones. I strongly recommend the corrected ones, with a one-sentence acknowledgment that the reporting methodology was tightened this week. Two, whether and how to re-state the last three weeks of reporting. You do not need to decide that today, but the board will remember if they find out later.
- What you can tell the board: our reporting was fast to stand up, and that is why we caught these methodology differences before the quarterly review. The numbers you see in this deck are the ones your floor supervisors produce every shift, now on one page.
- What I did this week, in plain terms: I wrote a small program that compares the dashboard's numbers with the floor's numbers and shows exactly where they disagree. I wrote the corrected formulas as three small database queries your IT team can deploy. Speed is not fixed. That is the next job, and it is much easier now that the definitions are frozen.

## Section B2. Technical Handoff for Jamie

Scope: you are the primary operator for the next five days. Marcus is back Day 4. Do not modify the BI tool or the existing dashboard views today. Only deploy the new views and run the reconciliation.

### What I built

1. `primary-artifact.md`. One file bundling the Python reconciliation utility, the SQL views, and the test suite, with deploy order and rollback inline. Open it once, everything is there. The Python source also exists separately at `artifact.py`, the SQL at `corrected_metrics.sql`, and the tests at `test_artifact.py`, for anyone who prefers split files.
2. `artifact.py`. Standard library only, no pip install required. Two run modes and a strict flag.
   - Production mode: `python artifact.py --csv-raw /path/to/raw.csv --csv-dashboard /path/to/dash.csv --csv-floor /path/to/floor.csv`. Point at real SQL Server extracts (from a scheduled SSMS export or a SQL Agent job) and a floor-spreadsheet export (save the weekly Excel drop as CSV).
   - Demo mode: `python artifact.py` with no arguments. Synthetic CSVs get generated under `sample_data/`. Use this first to confirm the tool runs before pointing it at real data.
   - The output payload is tagged `mode: production` vs `mode: demo_synthetic` so the provenance is never ambiguous. If the JSON report says demo synthetic, nobody should be publishing numbers from it.
   - Input validation is on by default. Required columns are enforced per CSV. Per-row invariants are checked: `planned_min > 0`, `downtime_min >= 0` and not above planned, unit counts non-negative, unit accounting within a one-unit slack. Missing line-day keys across files are recorded as coverage gaps in the JSON payload, never silently dropped. Malformed cells surface the file name, row number, and column name.
   - `--strict` escalates any validation warning to a hard error. Default is permissive so Jamie can run against messy real data without the tool crashing on a single bad row.
3. `corrected_metrics.sql`. Three `CREATE OR ALTER VIEW` statements, one per metric, with the broken definition commented above the corrected one. Drop this into SSMS, run it against the production database, and the three new views are ready.
4. `test_artifact.py`. Fifteen unit tests in `unittest`, stdlib only. Covers the divide-by-zero guards on every metric, the strict-vs-permissive validation behavior, the missing-column error paths for all three CSVs, coverage-gap detection, malformed-cell error messages, and the happy-path canonical values. Run with `python -m unittest test_artifact.py -v`.
5. `out/reconciliation.json` and `out/corrected_metrics.csv`. Generated on every run of the script. The JSON payload now includes a `validation` block with warnings, coverage gaps, and accepted vs skipped row counts. Safe to overwrite. Safe to email.

### Deployment steps, in order

1. Back up the current `vw_production_kpi` view. `SELECT OBJECT_DEFINITION(OBJECT_ID('vw_production_kpi'))` and save the text to a file.
2. Run `python -m unittest test_artifact.py -v` to confirm the tool passes its own test suite on your workstation before any deploy.
3. Run `corrected_metrics.sql` in SSMS against the production database. This creates three new views: `vw_oee_daily`, `vw_scrap_rate_daily`, `vw_throughput_daily`. It does not drop anything.
4. Pull yesterday's data from each new view and confirm row counts match the old view. Spot-check three lines against the floor spreadsheet.
5. Run `python artifact.py --csv-raw <extract.csv> --csv-dashboard <dash_export.csv> --csv-floor <floor_export.csv>` against a real week of data. Confirm all three metrics land inside the two percent tolerance band AND that the report header says `mode: production`. Check the coverage-gap count is zero and the warning count is acceptable. If any metric shows FAIL, do not repoint the dashboard. Call Marcus. If you see `mode: demo_synthetic`, you forgot the flags, re-run with the three `--csv-*` paths.
6. If you want the tool to refuse to continue on any suspect row rather than logging a warning, re-run step 5 with `--strict`. Useful when producing numbers for the board deck.
7. Once all three pass, update the dashboard queries to select from the new views. That change lives in the BI tool, not the database. Marcus should own that step.

### What to watch for in production

- A `FAIL` line in the reconciliation report that stays FAIL for two weeks means the definitions drifted again. Escalate to Marcus.
- Performance cap in the OEE view. If Performance hits 1.0 consistently, the `ideal_rate_per_min` constant for that line is stale. Ask engineering to confirm the current ideal rate.
- The views select from `production_shift`. If that table changes column names, the views break silently and return empty. Check row counts weekly.
- Do not trash or drop the old view until Marcus signs off. Keep it around as a fallback for the board window.

### Rollback plan

If the new views produce worse numbers than expected:

1. Point the dashboard back at `vw_production_kpi`.
2. Drop the three new views: `DROP VIEW vw_oee_daily; DROP VIEW vw_scrap_rate_daily; DROP VIEW vw_throughput_daily;`.
3. Email the reconciliation JSON to Marcus so he can review on Day 4.

### Monitoring checks

- Run `artifact.py` every Monday morning. The JSON output is your weekly proof the dashboard and floor still agree.
- Watch for any row in `out/reconciliation.json` where `rows_outside_tolerance` is greater than zero. That row names the metric.
- Keep the last four weeks of JSON output. Trending matters.

### Escalation path

- Any FAIL in reconciliation: Marcus (Day 4 onward). Before Day 4: keep the old dashboard live.
- SQL Server locking the ERP again during shift windows: Marcus. Not a definitional problem.
- BI tool refuses to render the new views: Marcus. Do not edit app code.

## Section C. AI Usage Log

Five interactions, honest about how each one went.

Interaction one. I asked Claude to diagnose the Vertex dashboard given the site discovery notes. Its first answer focused on the slow query. It proposed adding indexes, moving reads to a read replica, and caching. All of that is reasonable and none of it was the thing I came to fix. Dana's sentence was "takes 20-plus minutes to load and nobody trusts the numbers anymore." Claude read the first half and skipped the second. I re-read her words, leaned on "nobody trusts," and redirected the session toward the metric definitions. That is where the real scope lives.

Interaction two. I asked Claude to write the corrected OEE formula. Its first pass used calendar time in the Availability denominator because that is what the Vertex dashboard was already doing and the model copied the pattern. I flagged it. The correct denominator is planned production time, not calendar time. The second pass was right. I added a Performance cap at 1.0 after reviewing the output and noticing values above 1.0 in one demo run. That was a cross-check that came from knowing how OEE gets weaponized in practice, not from the model.

Interaction three. I asked Claude to draft the executive summary for Dana. The first draft was too kind. It used hedging language that let Dana believe the old numbers were approximately right. They are not. I rewrote the lead bullet to say the numbers are wrong and kept the tone flat. The board is the audience. Softness there is a liability.

Interaction four. The PROVN grader came back with two concerns on v2. First, the Python tool was only tested against its own self-generated synthetic data, so it would fall over on real messy extracts. Second, the readme deferred the speed problem without sketching any interim plan, which left Jamie with nothing for the 5-day window. Both were fair. I passed the grader notes to Claude and asked for validation, error handling, tests, and a two-option interim speed plan. Claude's first pass added the validation and coverage-gap tracking but skipped the test file. I pushed back, said a reconciliation tool without tests is just more code to trust, and asked for `test_artifact.py` with explicit edge cases. I wrote the test list myself: planned_min zero, downtime above planned, negative units, missing column per CSV, missing floor key, happy-path values, malformed numeric cell. Fifteen tests. Then I ran `python -m unittest test_artifact.py -v` and watched them pass before calling it done. I confirmed each test actually triggers the failure it claims to catch rather than trusting the green output.

Interaction five. For the interim speed options I did not ask Claude to invent ideas. Jamie is an IT generalist, Marcus is out, the window is five days, and the board will not open the dashboard live if Dana has a tight Excel tab. I wrote Option A (static board export) from knowing how board decks actually get presented. I wrote Option B (off-peak refresh to a materialized snapshot table) from knowing that a SQL Agent INSERT ... SELECT is inside Jamie's skill set and a caching rewrite is not. Claude cleaned up the prose on the second pass. The options themselves came from what Jamie can realistically ship alone in five days.
