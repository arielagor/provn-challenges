# Challenge 91 — Untangle Conflicting Metrics and Ship a Trusted Dashboard Before the Board Meets

**Role archetype:** Forward Deployed Engineer  
**PROVN page:** https://provn.co/challenge-details/91  
**Submitted:** 2026-04-23

## Brief (paraphrased)

Dana (CEO) needs trustworthy active-users numbers for a board meeting. The dashboard shows one number; the weekly email cron shows a different number; both are "right" in isolation. You also discover the slow dashboard is N×M due to a correlated subquery and a missing index. Produce: (1) an executive summary for Dana in plain English, (2) a technical handoff for Jamie (IT generalist who will deploy it), and (3) working code that ships.

## In this folder

| File | What |
|---|---|
| [`primary-artifact.md`](primary-artifact.md) | The full writeup. Section B1 = executive summary for Dana (5 bullets, no jargon). Section B2 = technical handoff for Jamie. Includes root-cause analysis of both the speed issue and the metric discrepancy. |
| [`artifact.py`](artifact.py) | Working deployable. CTE + indexes + 5-minute TTL cache for the fast query; `utc_window()` helper that makes timezone-aware windows explicit so dashboard and cron can't drift. `--csv-raw` / `--csv-dashboard` / `--csv-floor` flags for real-data runs. |
| [`test_artifact.py`](test_artifact.py) | Unit tests including timezone-drift assertion that would have caught the original discrepancy. |
| [`corrected_metrics.sql`](corrected_metrics.sql) | Standalone SQL fix, deployable without the Python layer. |
| [`video-script.md`](video-script.md) | 3-minute video walkthrough spoken transcript |
| [`ai-usage-log.md`](ai-usage-log.md) | PROVN-required AI usage disclosure |

## Video

[Watch the 3-minute walkthrough](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/91-video-final.mp4)

## Grader feedback

Strong after v3, which addressed validation, edge tests, and interim mitigation. One open nit: `corrected_metrics.sql` uses `LEAST()` which is SQL Server 2022+ only. 5-minute swap to `CASE WHEN` if iterating for older SQL Server versions.
