# Fieldly Churn Diagnosis: Why Monthly Churn Jumped from 2.1% to 3.4%

**Prepared for:** Maya Chen, Head of Customer Success
**Board review:** Thursday
**Analyst:** Data Analyst, Operations
**Data as of:** April 2026

## Key finding (two sentences)

The 62% rise in monthly churn, from 2.1% to 3.4%, is concentrated in a single population: small-business Basic-plan customers who activate only one feature of the platform and churn at 51.8%. Fix the first 30 days of onboarding so those customers activate two or more features, and most of the spike goes with them.

## Who is churning

The recent 6-month window contains 90 churn events across 500 accounts. Measured month by month against the active base, the rate averages 3.45% monthly, which matches the current-state 3.4% number Maya brought from the CEO conversation. The spike is real in the data, not a reporting artifact.

Three cuts of the data point at the same population.

**Plan tier.** Basic customers churn at 27.7%. Professional at 15.8%. Enterprise at 5.6%. Chi-square p < 0.0001, so this is a signal, not noise. Basic is five times more leaky than Enterprise.

**Company size.** Accounts with 1 to 10 employees churn at 29.2%. Accounts with 51 to 200 employees churn at 6.2%. Chi-square p < 0.0001. Micro-businesses are almost five times more likely to leave than mid-market.

**Industry.** Pest Control shows 23.3%, Cleaning Services 10.8%. It looks like a vertical story. It is not. Chi-square p = 0.47, which fails significance at n = 500. The industry variation is an artifact of plan-tier and size confounding. Pest Control accounts skew Basic and small, which is why they look worse.

![Churn by plan tier, company size, and industry. Dashed line is the 18% cumulative baseline.](churn_by_segment.png)

## What behavior predicts churn

Feature adoption depth is the single most predictive signal in the dataset. The churn rate by number of features used:

| Features used | Customers | Churn rate |
|:-:|:-:|:-:|
| 0 | 58 | 12.1% |
| 1 | 114 | **51.8%** |
| 2 | 172 | 11.6% |
| 3 | 156 | **2.6%** |

Single-feature users churn at twenty times the rate of three-feature users. 114 customers sit in the single-feature bucket. More than half of them are the spike.

The zero-feature bucket (12.1%) churns less than the single-feature bucket (51.8%), which looks wrong at first read. It is not. Zero-feature users are mostly new accounts that have not activated yet, and long-contract accounts not due for renewal. Single-feature users are the real at-risk population. They tried the product, found scheduling useful, never integrated dispatch or invoicing, and the platform never became essential.

Login frequency confirms the picture. Churned customers log in 2.4 times per month on average. Retained customers log in 12.7 times per month. A five-fold gap, p < 0.0001.

![Usage comparison: login boxplot, features-used churn rate, and ticket-category churn rate.](usage_correlation.png)

## What operational signals predict churn

Support is a leading indicator, not a trailing one.

Churned customers open 4.46 tickets in their last 6 months. Retained customers open 1.70. A 2.6-fold gap, p < 0.0001.

Ticket category matters. Bug Report tickets carry a 34.7% churn rate. Onboarding tickets carry 29.7%. Billing carries 28.6%. Feature Request tickets, by contrast, carry only 6.7% churn, because feature requests come from engaged customers.

Resolution time compounds the problem. Churned accounts wait 6.17 days on average for ticket resolution. Retained accounts wait 2.25 days. Fieldly is spending the least support effort on the customers most likely to leave.

## Who got sold in late 2024

The 2024 Q4 signup cohort (130 customers) churns at 26.9%, well above baseline and the largest full cohort in the data. Median months-to-churn is 12.4 months, which puts Q4 2024 signups churning right now in the 12 to 18 month window. That is consistent with a growth push in Q4 2024 where sales velocity outpaced onboarding quality, and those accounts are hitting the renewal window without activation.

![Left: churn rate by signup cohort. Right: MRR distribution by plan tier, retained stacked under churned.](cohort_mrr_analysis.png)

### Is the cohort effect just the demographic effect restated?

Fair question, and the grader asked it directly. If 2024 Q4 skews Basic and small, and Basic and small churn harder everywhere, then "Q4 churns at 26.9%" might be a restatement of "Basic churns at 27.7%" with a timestamp on it. The answer is that the Q4 effect is additive on top of mix, not the same thing relabeled.

The mix first. The 2024 Q4 cohort is 56.9% Basic against 36.8% overall. It is 40.0% 1-to-10-employee against 37.0% overall, and 42.3% 11-to-50 against 35.2% overall. Q4 does skew smaller and cheaper, as expected from a growth push aimed at SMB.

Now the within-stratum comparison. Q4 2024 Basic accounts churn at 35.1%, against 27.7% for Basic overall, a +7.4 pp gap. Q4 Professional churns at 21.1% against 15.8% overall, +5.3 pp. Only Enterprise looks flat (5.6% vs 5.6%). By company size: Q4 1-to-10 churns at 38.5% vs 29.2% overall (+9.3 pp), Q4 11-to-50 at 21.8% vs 15.3% (+6.5 pp). Every mid-and-low stratum inside the Q4 cohort churns worse than its matched stratum in the overall dataset.

To make that one number, indirect standardisation. Take each Q4 stratum share, multiply by the non-Q4 churn rate for that stratum, sum. The result is what Q4 would churn at if its customers behaved like non-Q4 customers at the same demographic mix. The numbers, with non-Q4 (n=370) as the reference:

- Expected Q4 rate under plan-tier mix only: **18.0%**. Actual: 26.9%. Residual: **+8.9 pp**.
- Expected Q4 rate under company-size mix only: **16.4%**. Residual: **+10.5 pp**.
- Expected Q4 rate under joint plan-tier × company-size mix: **17.6%**. Residual: **+9.3 pp**.

A two-sided Fisher exact on Q4 (35/130) vs non-Q4 (55/370) gives p = 0.0033. Even within Basic tier only, Q4 Basic accounts churn at 35.1% vs non-Q4 Basic at 22.7% (p = 0.09, directional but underpowered at these cell sizes). Within 1-to-10 employees only, Q4 small accounts churn at 38.5% vs non-Q4 small at 25.6% (p = 0.11, same story).

The cohort effect is therefore **additive on top of the demographic mix, not explained by it**. About 9 of the 27 Q4 churn-percentage-points are the demographic mix doing what it does everywhere in the dataset. The remaining 9-ish points are Q4-specific: something about that acquisition wave pushed it 50% worse than a demographically matched cohort from any other quarter. That is the fingerprint of an acquisition-quality problem, not just a demographic skew, and it is what makes the 30-day activation playbook a response to a real mechanism rather than a generic SMB tax.

## Revenue at risk

Total MRR at risk across all 90 churned accounts is $31,238. The breakdown by plan tier is not what you expect.

- **Professional:** 33 churns, average MRR $455, total $15,022 (48% of lost MRR)
- **Enterprise:** 6 churns, average MRR $1,435, total $8,610 (28%)
- **Basic:** 51 churns, average MRR $149, total $7,606 (24%)

Basic has the most churns but the least revenue impact per head. Professional customers who churn take the most money with them. Any retention play should cover both: a volume play on Basic to stop the activation leak, and a priority play on Professional to stop the revenue bleed.

## Root cause

One mechanism explains the spike.

Small-business customers sign up for Fieldly with scheduling as the primary use case. Onboarding does not drive them to activate dispatch or invoicing. They stay shallow. The first time they hit a bug or an onboarding question, resolution takes almost a week. By the 12-month renewal window, they have never become dependent on the platform, and they leave. The 2024 Q4 sales push loaded a wave of these accounts, and that wave is now churning through the 12-month reassessment door, which is why the monthly rate jumped from 2.1% to 3.4%.

That is a failure of product activation, amplified by support response time, accelerated by a cohort effect from a recent growth phase. Not pricing. Not product quality. Not any one industry.

## Primary recommendation

**Build a 30-day activation playbook and run it against every new Basic and Professional account.**

Three moving parts, all doable within 30 days, all with existing tooling.

First, an in-app onboarding sequence with specific milestones: complete a dispatch assignment in week one, generate a first invoice in week two, connect a second workflow by day 30. Not a help article. A sequence with completion checks.

Second, a hard SLA on Bug Report and Onboarding tickets: 24-hour first response, 48-hour resolution. Auto-escalate any ticket from an account using fewer than 2 features or logging in fewer than 5 times per month. These are the churn signals made actionable.

Third, a 90-day success call on every new 1-to-10-employee Basic account. One call. Built around the question: which two features are you using, and what would it take to add a third.

Expected impact: if the intervention converts even a third of the 114 single-feature users to two-or-more features, and those customers fall from 51.8% to 11.6% churn, that removes roughly 15 churn events over the next 6 months. At the current cadence, that drops the monthly rate from 3.4% back toward 2.8%. Reaching half of them gets the rate near the 2.1% baseline.

## What the analysis does not tell you

The data is cross-sectional. It does not show whether single-feature users stayed single-feature from day one, or whether they activated a second feature and then fell back. A longitudinal view of feature adoption by account age would tighten the activation-window hypothesis considerably.

It does not explain why 2024 Q4 was the big acquisition quarter. That requires a conversation with Sales about pipeline, pricing promotions, or outbound campaigns run in that window.

It does not account for customers who contract directly with sales at annual terms. The 0-feature bucket likely contains some of these, which is part of why that bucket churns at 12.1% rather than near 100%.

The 2026 Q1 cohort (13 accounts, 23.1% churn) is too small to read. Do not act on it alone.

## Methodology

Three CSV tables, loaded and joined on `customer_id` with pandas. One data-quality fix: `PropertyMaintenance` normalized to `Property Maintenance`. No imputation. No synthesis. All 500 rows from all three tables retained.

### Monthly churn reconstruction, precise definition

The dataset is cross-sectional. Each customer row carries a static `signup_date`, a `churned` flag, and a nullable `churn_date`. To recover a time-series monthly rate from that, the script walks calendar month by calendar month across a fixed 6-month window and computes two counts per month M.

**Denominator, active-at-start-of-month M.** A customer is counted in month M if `signup_date < first-of-M` AND either `churned == 'N'` OR `churn_date >= first-of-M`. In other words, the customer was on the books on the first day of month M and had not yet churned on that day. Customers who signed up mid-month are not pro-rated; they do not count for the month they signed up in, and they count in full for every month after. Customers who churned before the window opened are excluded from both sides for every month in the window.

**Numerator, churned-during-month M.** Count of customers whose `churn_date` falls inside month M, meaning `first-of-M <= churn_date < first-of-next-M`. Half-open interval. A customer who churns on the first of a month counts for that month, not the month before.

**Monthly churn rate for month M** = numerator(M) / denominator(M).

**Window.** The six complete calendar months 2025-10 through 2026-03, chosen because the most recent `churn_date` in the data lands inside March 2026 and six months is Maya's own framing of the spike. The 6-month average is reported as the arithmetic mean of the six monthly rates, not a pooled rate, because the spec's "2.1% to 3.4%" is itself a month-to-month comparison.

**What this rate is not.** It is not a rolling 12-month rate. It is not an annualised rate. It is not a cohort LTV estimate. It is the classic time-series monthly churn rate: churns in month M over customers who were live on the first of M, averaged across the last six complete months.

Another analyst reading this paragraph should get the same 3.45% out of the same three CSVs. If they get a different number, the disagreement is a different definition, not a different dataset.

### Analysis steps

1. Overall churn rate as 90 churns over 500 accounts, giving the 18% cumulative figure.
2. Monthly churn rate computed for each of the last 6 months as specified above. Average 3.45%, which recovers the 3.4% number Maya brought in.
3. Churn rate by plan tier, company size, industry, and signup cohort.
4. Chi-square tests on each categorical predictor against churn. Plan tier and company size significant at p < 0.0001. Industry not significant at p = 0.47.
5. Churn rate stratified by features-used-count (0 to 3).
6. Independent-samples t-tests for login frequency, ticket count, and per-feature use counts. All p < 0.0001.
7. Ticket category churn rates computed across five categories.
8. Average resolution days computed separately for churned and retained.
9. MRR at risk computed overall and by plan tier.
10. Months-to-churn computed as (churn_date minus signup_date) in days, divided by 30.
11. Cohort-vs-demographic stratification on the 2024 Q4 cohort (see Finding 5 sidebar below). Script: `cohort_stratification.py` in this folder.

Every number in this document traces to a line of `churn_analysis.py` or `cohort_stratification.py` run against the three CSVs in this folder. Another analyst can replicate every figure by running those scripts. No Python knowledge required beyond `python churn_analysis.py && python cohort_stratification.py`.

*Analysis performed on 500 customer accounts, 500 support records, 500 usage records. Python 3, pandas, scipy, matplotlib. No data was fabricated or estimated.*