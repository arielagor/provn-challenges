# Challenge 97 — Diagnose a 62% Spike in Churn Before the Board Meeting

**Role archetype:** Data Analyst (McKinsey-level)  
**PROVN page:** https://provn.co/challenge-details/97  
**Submitted:** 2026-04-23

## Brief (paraphrased)

You're the data analyst at a B2B SaaS. Churn is up 62% quarter-over-quarter. Board meets Thursday. Diagnose the cause from three real CSVs (customers, support tickets, usage), produce an executive-ready writeup with charts, and make a specific, actionable recommendation backed by significance tests. Cannot fabricate numbers.

## In this folder

| File | What |
|---|---|
| [`analysis-document.pdf`](analysis-document.pdf) | Primary deliverable shipped to PROVN. 7 pages, 3 charts embedded inline. |
| [`analysis-document.md`](analysis-document.md) | Same analysis in Markdown. |
| [`churn_analysis.py`](churn_analysis.py) | Full reproducible analysis. Loads the CSVs, runs the significance tests, produces the three charts. |
| [`cohort_stratification.py`](cohort_stratification.py) | Cohort stratification helper used in the analysis. |
| [`data/`](data/) | The three source CSVs (customers, support, usage) — 500 rows each, synthetic. Included so the analysis is fully reproducible. |
| [`charts/`](charts/) | The three charts embedded in the PDF (churn by segment, cohort MRR analysis, usage correlation). |
| [`video-script.md`](video-script.md) | 3-minute video walkthrough spoken transcript |
| [`ai-usage-log.md`](ai-usage-log.md) | PROVN-required AI usage disclosure |

## Video

[Watch the walkthrough](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/97-video-final.mp4)

## Key findings

- Overall churn: **18.0%** (90 of 500 customers), **$31,238 MRR at risk**
- Top finding: feature adoption depth. 1 feature = 51.8% churn; 3 features = 2.6%. **20× spread, p < 0.0001**
- Support resolution: bug tickets churn at 34.7%. Churned customers waited 6.17 days on average for bug resolution vs 2.25 days for retained customers.
- Industry variation NOT significant (p = 0.47) — prevents a misleading vertical narrative.

## Grader feedback

Strong after v4 (v4 embedded the charts visibly in the PDF which addressed the prior pass's "charts missing from PDF" nit). One dataset-level critique remains (3.45% monthly rate is somewhat tautological given cross-sectional data) — acknowledged in the methodology section. Can't generate event-time data from a cross-sectional snapshot.
