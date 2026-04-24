# Meridian AI Assistant, Phase 1 Product Brief

**Author:** PM, AI Assistant
**Audience:** CPO, Engineering, CS, Legal
**Status:** Pre-kickoff draft, for review in 4 days
**Horizon:** Now to Q2 ship, 6 weeks, 3 full-stack engineers, no ML team

## Problem framing

Meridian sells a BI platform to 250+ mid-market companies. Retention is strong. Competitive pressure is not. AI-native entrants ship automated insight generation out of the box, and the CPO has already sold an AI Assistant into four enterprise contracts on a Q2 delivery commitment. Missing the date puts those renewals at risk.

What the Assistant needs to do for users: let an operations or finance analyst ask a plain-language question against data they already trust in Meridian, get a chart or summary back in under a minute, and know when not to trust the answer. What it needs to do for the business: prove that Meridian can ship credible AI in a field where one competitor already shipped an embarrassment, and do it inside a quarter, without hiring a model team.

Two failure modes matter more than the rest. One: shipping late and losing the four signed enterprise renewals. Two: shipping on time with an answer that hallucinates a financial number and becoming next year's cautionary case study. Phase 1 is designed around avoiding both.

## Feature scope

**In Phase 1.**
Natural-language question box inside an existing dashboard context. The user picks a dataset or a dashboard, then asks a question against it. The Assistant turns the question into a SQL query against Meridian's existing semantic layer, executes it, renders a chart using the same chart primitives the dashboard tool already renders, and writes a two to four sentence summary of what the chart shows. Every answer carries the SQL that was run, the row count, and a confidence note. The user can see the query, edit it, and rerun. An "explain this chart" action runs on charts the user already has. Feedback thumbs on every response.

**Explicitly out of Phase 1.**

Cross-dataset joins the user did not pre-author. Free-form "recommend what I should do next" prose that goes beyond what the data shows. Write-back actions. Scheduled agentic runs. On-premise or in-VPC inference. Fine-tuned models. A separate chat surface outside the dashboard context. Voice. Multi-turn memory across sessions.

The cuts are deliberate. Cross-dataset joins need a governed join graph we do not have yet, and a wrong join silently produces a wrong number, which is the exact failure mode the competitor hit. Write-back is a blast-radius problem we do not want to carry into a six-week build. On-premise inference is out because it blocks on legal and on infrastructure Meridian does not own, and burning Phase 1 trying to solve it means shipping nothing.

## Architecture recommendation

Route through a single third-party LLM provider using a narrow, tool-calling contract. The model does not see raw customer data. The model sees the question, the schema of the dataset the user selected, and a list of allowed tools (run_sql against the semantic layer, render_chart against the existing chart library, summarize against a bounded result set). Queries run inside Meridian's existing query engine with the existing row-level permissions. Summaries run against already-filtered result sets, not raw rows, which keeps the blast radius of a prompt injection small.

**Cohort split.** Phase 1 ships to the non-residency-constrained customers only. That is the 246 of 250 accounts where data can legally leave Meridian's environment under the current master agreement. The four enterprise accounts with residency requirements are offered a clearly-labeled Phase 2 pathway, conditional on legal signing a standard data handling agreement and, if that agreement requires it, an in-region or in-VPC deployment. We tell them this explicitly, in writing, with a target window rather than a promise.

**Trade-offs accepted.**

Using a hosted LLM means we cannot serve the four residency-constrained accounts in Phase 1. That is the cost of shipping on time. Restricting the Assistant to single-dataset questions with a visible SQL trail means power users asking cross-dataset questions will hit the wall and feel the limit. That is the cost of avoiding the hallucinated-financial-summary failure. Deferring on-premise inference to Phase 2 means we will need to rebuild a piece of the serving layer when we bring those four accounts online. That cost is real, and it is smaller than the cost of trying to solve every cohort in six weeks.

## Three-milestone roadmap

**Milestone 1, end of Week 2. Thin end-to-end answer path.** One engineer owns the model contract and the tool layer. One owns the semantic-layer binding and SQL execution. One owns the dashboard UI surface. Goal at end of Week 2: an internal user can ask a question against one seeded dataset, get back a chart, a summary, the SQL, and a confidence note. No cohort gating yet. No feedback capture yet. No guardrails beyond "only the tools in the allow-list can run." This milestone exists because every risk we care about is real only once the full pipe is wired. Shipping a thin path first buys us four weeks of hardening against known failure modes.

**Milestone 2, end of Week 4. Trust surface and cohort gating.** Feedback thumbs wired and logged. Per-account feature flag driven by a cohort table that reads from the customer record. Accounts flagged as residency-constrained see a clear "coming in Phase 2" banner in place of the Assistant, with a link to the written Phase 2 pathway. A red-team pass on hallucination: a tester runs a fixed set of 50 seeded questions, we grade answers against a known-correct key, and we set a minimum pass rate before we let any external user touch the feature. A Customer Success playbook for the first ten users.

**Milestone 3, Week 6 ship.** Closed beta with 10 to 15 users across three of the non-residency customers we have existing relationships with. Ship is gated on the pass rate from Milestone 2, on zero P0 bugs open for 72 hours, and on CS having a runbook for the first week of support. Assuming all three gates pass, we open to the full non-residency cohort on a rolling basis over the two weeks after Q2 ship, not all at once.

Sequencing rationale. Every week not spent on the thin end-to-end path is a week where unknown integration problems hide. Milestone 1 exposes them. Milestone 2 spends the middle two weeks on the two things that actually kill this launch in public: a wrong answer and a residency breach. Milestone 3 spends the last two weeks proving the thing is safe with real users before opening the gate.

## Success metrics

Outcome-based, not output-based. Three, not three-as-decoration.

**Assistant-assisted BI session rate.** Percentage of weekly active BI sessions in the eligible cohort that include at least one Assistant interaction, measured four weeks after ship. This is the demand signal. If nobody uses it, nothing else matters.

**Median time from question asked to chart the user keeps.** Clock starts when the user types the question, stops when the user either saves the chart, exports it, or pins it to a dashboard. Discarded answers do not count. This is the value signal. It tells us whether the Assistant is actually shortening the path to an answer or just adding a step.

**Answer trust rate.** Percentage of Assistant responses that get a thumbs-up or an edit-and-rerun action, rather than a thumbs-down, an abandon, or a support ticket. Measured over a rolling 14-day window, reviewed weekly by PM and CS together. This is the safety signal. It is the number we watch to catch the competitor's failure mode before a customer catches it for us.

## Constraint acknowledgement

Every constraint named in the brief above is real and shaped this plan.

No internal ML team. The plan uses a hosted LLM and tool-calling, not a fine-tune. No model weights are owned by Meridian in Phase 1. The one ML engineer on staff is not on the project and does not need to be.

Data residency. Four enterprise accounts are carved out of Phase 1. They are offered a written Phase 2 pathway conditional on legal sign-off. They are not promised a date the engineering team cannot honor.

Three engineers, six weeks. The milestones are sized to this team. The scope cuts above exist because this team cannot ship a larger scope in this window without compromising the trust surface.

Trust concern after the competitor's failure. Every Assistant answer carries its SQL, its row count, and a confidence note. A red-team pass gates the ship. A CS runbook gates the ship. The success metric that watches for the competitor's failure mode is reviewed weekly by the people who would hear about it first.
