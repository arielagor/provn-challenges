# Challenge 94 | README

## Section A: Deal Assessment

Advance. This deal has real pain, named budget, and a buyer who has already done the homework of booking a competitor on top of us. Priya reached out because of a case study, which means she is pattern-matching Meridian to a problem she has already diagnosed. The technical fit is clean: Snowflake, dbt, Looker are three connectors we ship, not a custom integration request.

The single biggest risk to close is not Monte Carlo. It is the hidden $35K CFO sub-cap under the $50K CTO ceiling. If Priya cannot walk her CFO through a dollar-cost frame for the status quo, she stalls below our $45K quote and picks Monte Carlo on price alone. The demo has to leave her with CFO-ready language, not only a technical evaluation.

Next step I propose at end of call: a two-week technical proof on her real Snowflake plus dbt plus Looker instance, scoped to the three dbt models that caused last quarter's incidents. The proof produces a written incident ledger she can hand her CFO. I offer to co-attend the CFO conversation if helpful. Target close within twenty-one days.

## Section B: Internal Handoff Note to AE

**Customer:** NovaBuild, ~$60M construction tech. Priya Sharma, Head of Data Eng.

**Confirmed requirements:** Snowflake + dbt + Looker observability. 14 dbt models, 40+ Looker dashboards. Primary use case is preventing stale-data incidents from reaching sales and finance. Two-person data team, low ongoing ops overhead is mandatory.

**Budget:** CTO approved up to $50K. CFO wants written ROI above $35K. Effective ceiling is $35K until CFO is sold.

**Objections handled:** Price ($32K MC vs $45K us) answered by framing the $13K delta as less than one stale-pricing incident, plus lineage-based auto-pause of downstream Looker dashboards, which MC does not ship. Fit worry answered by connector-first setup and a commitment to under two eng hours per week after day thirty.

**Competition:** Monte Carlo. Already had discovery, preparing proposal. Price play.

**Next step:** two-week technical proof on real instance, scoped to the three incident-causing dbt models, produces CFO-ready ledger.

## Section C: AI Usage Log

### Interaction 1: Discovery Summary draft, then redirect on the implicit constraint

**Task assigned.** I asked Claude to draft the Discovery Summary section, specifically the "implicit constraint Priya has not explicitly stated" subsection. I fed it the pre-call notes verbatim and asked for two to three implicit constraints grounded in the numeric facts in the brief.

**What AI produced.** First draft returned three implicit constraints. The first two were strong: the $35K CFO sub-cap under the $50K CTO ceiling, and the 2.85x downstream multiplier (14 models to 40 dashboards). The third was generic: "Priya is likely feeling reputational pressure from stakeholders who have lost trust in the dashboards." That is a feeling claim, not a constraint, and it is not grounded in a fact from the pre-call notes. It is the kind of sentence that reads well and proves nothing.

**What I changed.** I rejected the third item entirely and replaced it with the "she is the second engineer" constraint, which I derived from the literal phrasing in the pre-call notes ("Our data team is two engineers, including me"). That is a head-count constraint with operational consequences, not a mood claim. I also asked Claude to re-ground the first two constraints in explicit math (the $13K delta sitting between the MC quote and the effective CFO ceiling; the 2.85 dashboards-per-model average). The re-ground produced the numbers you see in the brief.

**Why.** The spec is explicit: "grounded in a specific Meridian capability or measurable outcome, not generic reassurance." That rule also applies to discovery claims. A claim about Priya's feelings is not falsifiable on the call and cannot be tested in the demo. A claim about a $35K CFO sub-cap can be tested by asking one direct question. I want every claim in the brief to pass that test.

### Interaction 2: Objection 1 draft, then redirect away from feature-list reassurance

**Task assigned.** I asked Claude to draft Objection 1 (the $32K vs $45K price objection) with the suggested angle from the spec: "the cost of ONE more stale-dashboard pricing mistake outweighs the $13K delta."

**What AI produced.** First draft was a well-structured three-paragraph response. Paragraph one walked through ROI math. Paragraph two listed four Meridian capabilities Monte Carlo does not have: lineage-based auto-pause, a proprietary anomaly model, a broader connector catalog, and a richer incident ledger. Paragraph three closed with a commitment. The capability list in paragraph two is exactly what the spec warns against. It is a feature-list reassurance, not a specific measurable outcome tied to her pain.

**What I changed.** I kept paragraph one's ROI frame and kept paragraph three's close. I cut three of the four capabilities from paragraph two and kept only the lineage-based auto-pause, because that is the one capability that directly prevents the incident Priya described. I also added a live-call question: "On the two pricing decisions last quarter that went out on stale numbers, what was the difference between the quoted price and the correct price, and did any of those deals close?" That question turns the objection into a discovery moment and grounds the ROI frame in Priya's own numbers, not my estimates.

**Why.** Objection handling is not persuasion. It is re-anchoring the conversation on the prospect's own data. Four capabilities in a paragraph reads as selling. One capability plus a question reads as listening. The spec's scoring rubric weights competitive instinct, and competitive instinct in a head-to-head against Monte Carlo is not about having more features. It is about making the prospect's pain specific enough that the cheaper tool becomes obviously the wrong choice.
