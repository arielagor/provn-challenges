# Meridian Data | NovaBuild Discovery & Solution Brief

**Prospect:** Priya Sharma, Head of Data Engineering, NovaBuild
**Call:** 45 minutes, discovery + demo, Monte Carlo active in the deal
**Stack:** Snowflake + dbt + Looker. 14 active dbt models feeding 40+ Looker dashboards.

## Discovery Summary

### The technical problem, stated plainly

NovaBuild has a production data pipeline with no production-grade monitoring on it. Fourteen dbt models run on Snowflake, feed Looker, and reach sales, finance, and operations. When a model breaks, the first alert is a Slack message from a sales rep who just quoted a customer off stale revenue.

That has happened three times last quarter. Twice it reached sales before anyone caught it, and pricing decisions went out the door on old numbers.

### Root cause

Priya's team has built the pipeline. They have not built the pipeline's observability. dbt has `tests:` blocks, Snowflake has query history, Looker has its own health metadata, but nothing crosses the three surfaces. A failure in a dbt model test is invisible to Looker. A stale table in Snowflake is invisible to sales. Three independent systems, zero shared signal.

### Downstream impact

Two pricing mistakes on outdated revenue in a single quarter. The dollar cost of each is not yet documented, but the reputation cost inside the company is bigger than the dollar cost. Sales now doubts the dashboards. Finance now double-checks the dashboards. Operations now asks Priya's team to verify dashboards by hand before they act on them. Priya's two-person team has become a manual-QA function for its own pipeline. Every hour spent verifying numbers is an hour not spent building new models.

### Implicit constraints Priya has not named

**The budget is actually $35K, not $50K.** The CTO has approved up to $50K, but the CFO wants ROI framing before green-lighting anything over $35K. Priya has to sell a CFO she does not directly report to on a category the CFO does not think about. Without a clean dollar-cost frame on the status quo, she stalls at $35K, which is below Meridian's $45K quote and above Monte Carlo's $32K quote. The $35K ceiling is why Monte Carlo's price is attractive, not the $50K ceiling.

**Fourteen models fanning out to forty-plus dashboards is a 2.85x multiplier.** On average, one broken model corrupts almost three downstream Looker surfaces. Priya cannot fix stale data by patching dashboards reactively, because by the time three stakeholders complain she has three separate fires to put out and no single upstream source to look at. The math forces her toward upstream monitoring whether she has named that out loud or not.

**She is the second engineer.** "Two-person team including me" means she is writing dbt models herself, not only running the team. Any tool that requires a dedicated ops owner is disqualified on head count before it is evaluated on price. This is the real shape of the fit objection.

## Solution Narrative

The demo walks Priya's pain in the order she lives it, not the order Meridian's marketing site lists features.

### Pain 1: "I find out about failures from stakeholders"

**Before:** a dbt model test fails silently in the nightly run. Looker keeps serving the last-good table. Sales quotes a customer Tuesday afternoon. Wednesday morning a rep DMs Priya on Slack saying the number "looks off."

**Demo:** I pull up Meridian already connected to a test Snowflake + dbt + Looker environment mirroring NovaBuild's shape. I trigger a failing `dbt test` on a revenue model. Inside Meridian, the failure shows up in the single pane within seconds. The lineage graph lights up with the three downstream Looker dashboards that consume this model. Meridian auto-pauses those three dashboards by posting an "under review" banner through the Looker API, so sales never sees stale numbers.

**After:** the person who learns first is Priya, not a sales rep. The 2.85x downstream multiplier stops hurting her, because one upstream alert covers all three surfaces.

### Pain 2: "My team is two people, and I am one of them"

**Before:** Priya is both writing dbt models and fielding Slack DMs about dashboards. Every new pipeline change is a head-count decision.

**Demo:** I open Meridian's connector screen and show the Snowflake, dbt, and Looker connectors. They are pre-built. Auth once, scope the schemas, done. No extra schemas to create in Snowflake, no dbt macros to import, no Looker LookML to modify. Then I show the default alert rules that ship with the product: freshness SLA, test failure, schema change, volume anomaly, lineage impact. Priya does not configure thresholds. The thresholds are learned from the first two weeks of data and she tunes from the alerts, not from a config page.

**After:** the ongoing operational surface is a notification feed, not a configuration surface. Priya reviews alerts. She does not maintain the tool.

### Pain 3: "I need to tell my CFO why this is worth it"

**Before:** Priya can describe the incidents but cannot frame them in dollars the CFO will accept.

**Demo:** I open Meridian's incident ledger. Every detected issue gets a time-to-detect, a time-to-resolve, and a blast-radius count of affected dashboards and affected downstream users. I show how a three-month deployment gives her a written record she can hand the CFO: "three incidents detected upstream, zero reached sales, avoided N hours of manual reconciliation and X dollars of mispriced bids." The tool writes her ROI case for her.

**After:** Priya has a renewal conversation with her CFO that is grounded in her own data, not in a vendor deck.

## Objection Responses

### Objection 1: price. Monte Carlo is $32K, Meridian is $45K.

The $13K delta is roughly one stale-dashboard pricing mistake. NovaBuild had two of those last quarter. I do not know the exact dollar impact of each, and I do not want to guess, so I ask Priya directly: "On the two pricing decisions last quarter that went out on stale numbers, what was the difference between the quoted price and the correct price, and did any of those deals close?" Whatever number she says, Meridian pays for itself the first time it catches a similar incident.

The second piece is the lineage-based auto-pause. That is not a feature Monte Carlo ships today. Monte Carlo will tell her when a model breaks. Meridian will tell her and simultaneously gate the three Looker dashboards that consume it, so sales never sees the bad number in the first place. The value of the $13K delta is not a better alert. It is the prevention of the incident that produced the alert.

### Objection 2: fit. Two-person team, worried about ops overhead.

The two-person-team worry is a real worry, and it would be a valid worry for any data platform that requires configuration to produce value. Meridian is connector-first, not rule-first. The setup is: three OAuth flows, one schema-scope selection per source, one Slack or email destination. The first alerts fire within twenty-four hours without any thresholds written. The day-two experience is reviewing notifications, not writing YAML.

I would offer Priya a concrete commitment: if Meridian takes more than two engineering hours per week of her time after the first thirty days, we are not the right tool and we part ways. That commitment is easy for me to make because the product is built around connector-first ingest and learned thresholds, not because I am being generous.

## Close

The discovery brief and the demo point at the same recommendation: move forward to a two-week technical proof with Priya's real Snowflake + dbt + Looker instance, scoped to the three dbt models that caused last quarter's incidents. The proof produces the incident ledger Priya needs for her CFO. If the ledger shows zero caught issues, we walk. If it shows one, the $13K delta is already paid back.
