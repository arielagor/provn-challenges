# Fieldly Churn Diagnosis, README

**PROVN Challenge 97**
**Company:** Fieldly (B2B SaaS, field service teams)
**Stakeholder:** Maya Chen, Head of Customer Success
**Board review:** Thursday

## Section A: Written Analysis

### Diagnosis

Monthly churn at Fieldly rose from 2.1% to 3.4% over six months, a 62% increase. The rise is concentrated in one population. The monthly rate reconstructs month by month across 2025-10 through 2026-03: denominator is customers live on the first of the month, numerator is customers whose `churn_date` falls inside the month. Precise rule in analysis-document Methodology.

Feature adoption depth is the strongest behavioral signal. One-feature users churn at 51.8%, three-feature users at 2.6%. A twenty-fold gap, with 114 accounts in the single-feature bucket. The zero-feature bucket (58 accounts, 12.1%) is mostly new and annual-contract signups that have not activated yet.

Demographics line up. Basic-plan churn is 27.7%, Enterprise 5.6% (p < 0.0001). 1-to-10 employees churn at 29.2%, 51-to-200 at 6.2% (p < 0.0001). Industry looks meaningful but is not: p = 0.47. Pest Control and HVAC over-index because they skew small and Basic, not for vertical reasons.

Support confirms the mechanism. Churned customers open 4.46 tickets vs 1.70 retained, and wait 6.17 days for resolution vs 2.25. Bug Report and Onboarding tickets carry 34.7% and 29.7% churn. The customers needing help most sit in the longest queues.

The 2024 Q4 cohort (130 customers, the largest) churns at 26.9%. Median months-to-churn is 12.4, which puts Q4 2024 signups churning right now through the 12-to-18-month renewal window. A growth push at that time loaded a wave of under-activated accounts, and that wave is the spike. Controlling for mix (Q4 is 56.9% Basic vs 36.8% overall), indirect standardisation on joint plan-tier × company-size gives 17.6% expected, leaving a +9.3 pp cohort residual (Fisher p = 0.0033 vs non-Q4). The cohort effect is additive on top of demographics, not the same finding restated.

### Primary recommendation

Build a 30-day activation playbook for every new Basic and Professional account. In-app onboarding sequence with checkpoints (dispatch assignment in week one, first invoice in week two, second workflow by day 30). Hard 24-hour first-response and 48-hour resolution SLA on Bug Report and Onboarding tickets, with auto-escalation for accounts under 2 features or under 5 monthly logins. A 90-day success call on every 1-to-10-employee Basic account.

If a third of the 114 single-feature accounts move to two or more features, roughly 15 churns go away over six months, pulling the monthly rate from 3.4% toward 2.8%. Half gets it near 2.1%.

### Trade-offs

No pricing change on Basic: the data fits an activation problem, not a price problem. No industry playbooks: industry failed significance. No product redesign: 3-feature users churn at 2.6%, so the product works when customers reach it. Trading acquisition spend for retention spend this quarter.

### Limits

The data is cross-sectional. It does not show whether single-feature users started there or fell back. The 2024 Q4 acquisition wave needs a Sales conversation to explain. Annual-contract accounts likely sit in the 0-feature bucket, which is why that bucket churns at 12.1% rather than near 100%. The 2026 Q1 cohort is 13 accounts, too small to read alone.

## Section B: Stakeholder Brief

**For the board.**

Monthly churn rose from 2.1% to 3.4% over six months, a 62% increase, and almost all of it comes from one group: small customers on our Basic plan who only ever use one part of the product.

Customers who use one feature leave at 52%. Customers who use all three features leave at under 3%. This is not a pricing problem, a product problem, or an industry problem. Customers sign up, try scheduling, never connect dispatch or invoicing, and never make the platform essential. A year in, they leave. A growth push in late 2024 brought in a large wave of exactly these customers, which is hitting the renewal door now.

Here is what we should do. Build a 30-day activation path that walks every new customer through dispatch and invoicing, not a help article but a sequence with checkpoints. Put a 24-hour response SLA on bug and onboarding tickets, where customers who leave currently wait almost a week. Call every small Basic customer at day 90 to make sure they use more than one feature. No new tools, no new budget, 30 days of focus.

## Section C: AI Usage Log

I worked with Claude on this analysis. Three interactions materially shaped the result.

**1. Data first, then story.**

I asked Claude to propose an analytical plan before touching the CSVs. The first draft plan led with industry segmentation (HVAC vs Pest Control vs Plumbing), which matched the most visible cut of the data and would have produced a tidy vertical-specific narrative. I ran the chi-square test on industry and got p = 0.47, which fails significance. I told Claude we were not leading with industry. We re-ran the plan leading with plan tier and feature adoption depth, where the differences were real (p < 0.0001). What I kept: the overall segmentation-first structure. What I changed: demoted industry to a null-result finding instead of a headline, so the document shows the rigor rather than pretending the vertical story existed.

**2. Do not smooth the weird feature-adoption pattern.**

Feature adoption came out non-monotonic: 0 features = 12.1%, 1 feature = 51.8%, 2 features = 11.6%, 3 features = 2.6%. Claude's first draft flagged this as likely a data quality issue and proposed dropping the 0-feature bucket from the chart. I pushed back. The 0-feature bucket is most likely new and annual-contract accounts that have not activated yet, which is a real population with a real story. Suppressing the anomaly would have hidden the mechanism. We kept all four buckets and explained the shape in the document, which is what makes the 51.8% single-feature finding credible rather than noisy.

**3. Reconcile the 18% cumulative with the 3.4% monthly.**

Claude's first framing said "18% overall churn rate" and treated Maya's "2.1% to 3.4% monthly" as context. That buries the spike. I rewrote the lead so the 62% rise from 2.1% to 3.4% is the headline, with 18% as a cumulative cross-check. I then added a monthly-churn block to churn_analysis.py that computes active-at-start-of-month and churned-during-month, recovering a 3.45% average over the last 6 months of data, which matches the 3.4% number Maya brought in. That connects the dataset back to the spec's framing. Keeping the cumulative 18% also gave the report a second anchor when the monthly math gets challenged at the board.

**4. Grader pushback on methodology opacity and cohort independence.**

A grader pass flagged two gaps. First, the 3.45% monthly reconstruction was described at a high level but the exact denominator was not pinned down, which meant another analyst could plausibly build it differently and get a different number. Second, the 2024 Q4 cohort finding never checked whether the cohort effect was independent of plan tier and company size, so it might have been a restatement of "Basic customers churn harder" with a timestamp on it. Both fair. I told Claude to stop defending and make the fixes. For the methodology, I had it write an explicit sidebar in the Methodology section specifying the half-open-interval numerator rule, the strict-inequality denominator rule, the no-pro-rating assumption for mid-month signups, and what the rate is NOT (not rolling 12-month, not annualised, not cohort LTV). For the cohort independence question, I had Claude write cohort_stratification.py, which ran indirect standardisation against the non-Q4 reference population: Q4 2024's actual 26.9% rate against an expected 17.6% under joint plan-tier × company-size mix, leaving a +9.3 pp cohort-specific residual. Fisher exact Q4 vs non-Q4 is p = 0.0033. That resolves it: the cohort effect is additive on top of the demographic mix, not the same finding relabeled. Both findings are now in analysis-document.md with the real numbers from cohort_stratification.py.

*All numerical claims in this README trace to churn_analysis.py and cohort_stratification.py. Running both scripts against the three CSVs in this folder reproduces every number used above.*