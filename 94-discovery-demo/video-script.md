# Challenge 94 | Video Script (~3 min)

## 1. Discovery reasoning (~60s)

The problem is not that a dbt model broke. It is that a sales rep found out first, after quoting a customer on the stale number. Fourteen dbt models feed forty-plus Looker dashboards. Three failures last quarter, two reached sales. dbt, Snowflake, and Looker each have their own health signals and none cross over.

Two things beyond the pre-call notes. First, the $50K CTO budget is not the real ceiling. The CFO wants ROI framing above $35K, which puts her effective budget three thousand above Monte Carlo and ten thousand below us. Without CFO-ready language, she picks the cheaper tool on price alone. Second, fourteen models into forty dashboards is almost three per model. Reactive patching cannot work. The math forces upstream monitoring.

## 2. Demo structure (~50s)

I walk her pains in the order she lives them. First: she finds out about failures from stakeholders. I show a failing dbt test, lineage lighting up three Looker dashboards, auto-pause so sales never sees the bad number. Second: two-person team. Connector-first setup and learned thresholds, so day two is a notification feed, not a configuration surface. Third: she has to sell her CFO. I show the incident ledger that writes her ROI case in her own data. Order matters: the first two pains earn the right to talk about the third. If I open on ROI, I sound like a vendor.

## 3. Objection handling (~55s)

I take the price objection. Monte Carlo quoted thirty-two, we quoted forty-five. My response starts with a question back to her: on the two pricing decisions last quarter that went out on stale numbers, what was the dollar gap, and did those deals close? Whatever she says, thirteen thousand is almost certainly less than one of those mistakes. That reframes price from two invoices into one invoice against one incident.

Then I name the capability that pays for the delta: lineage-based auto-pause. Monte Carlo alerts when a model breaks. We alert and we gate the downstream dashboards, so sales never sees the broken number. The delta is not a better alert. It is prevention.

## 4. Mandatory AI question (~45s)

I asked Claude to draft the implicit-constraint section. It returned three. Two were strong: the $35K CFO sub-cap and the 2.85x dashboard multiplier, both grounded in the numbers. The third was a sentence about Priya feeling reputational pressure from stakeholders. That reads well and proves nothing. It is a feeling claim, not a falsifiable constraint. I cannot test it on the call or demo against it. So I cut it and replaced it with the "she is the second engineer" constraint, from the literal phrasing: "two engineers, including me." That is a head-count fact with operational consequences. Every claim has to be testable. If Claude writes one that is not, I cut it.
