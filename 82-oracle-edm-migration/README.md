# Oracle EDM Cloud Consultant Submission: Meridian Financial Group

**Author:** Ariel Agor
**Engagement:** Migration from on-premise Oracle EDM (Primous) to Oracle EDM Cloud
**Window:** 12 weeks, no buffer past Week 12

## Section A: Migration Risk Assessment

The fiscal year-end close opens at Week 14, two weeks after the migration window closes. There is no slack. The risks below are ordered by combined probability and impact, with the highest-cost risk first.

### Risk 1: FCCS metadata mismatch at cutover blocks the year-end close

**What could go wrong.** The FCCS member mapping or hierarchy structure in EDM Cloud diverges from what FCCS expects. Symptoms appear as failed metadata loads, broken consolidation rules, or intercompany elimination errors. The fiscal close opens with FCCS unable to consume the current hierarchy.

**How I detect it.** Reconciliation Checkpoint 2 at end of Week 8 includes a full FCCS test sync on a frozen-as-of-Week-7 dataset. The trial balance from EDM-Cloud-fed FCCS must match the same period's Primous-fed actuals to the penny. Any variance triggers root cause analysis before we touch production.

**Contingency.** Three layers. First, the parallel validation week (Week 13 soak period) gives a final detection window before the close opens. Second, Primous remains read-only available through Week 13 as a rollback option, since the on-premise license overlap covers this. Third, if a metadata defect is discovered post-cutover during the close cycle, a documented manual override path lets Corporate Accounting commit hierarchy hot-fixes directly into FCCS during a single emergency window, with the EDM Cloud catch-up applied within 48 hours.

### Risk 2: Validation pre-pass surfaces hundreds of legacy data quality issues that overwhelm the governance team

**What could go wrong.** Primous's looser validation regime means there are nodes in production today that violate EDM Cloud's tighter rules: balance type mismatches, orphaned intercompany pairs, parent nodes with balance types, FCCS member names with disallowed characters. The validation pre-pass at Week 7-8 may produce hundreds of exceptions that the small data governance team cannot triage in the remaining four weeks.

**How I detect it.** A dry validation pass against the Week 1 extract is run in Week 4 (a month before the formal pre-pass) specifically to size the exception backlog. If the exception count is materially above expectation, escalate before sinking weeks of design time into a plan that the data quality work cannot support.

**Contingency.** Two levers. First, prioritize exceptions by FCCS impact: nodes that block consolidation get fixed immediately, nodes with cosmetic violations get a temporary "legacy exception" property that grandfathers them in, with a documented post-go-live cleanup queue. Second, if the volume is too high to triage in the window, scope down the EDM Cloud validation rules at go-live (turn the cosmetic ones to soft warnings) and re-tighten in a phase 2 hardening pass after Q1 close.

### Risk 3: Stakeholder resistance from teams comfortable with the Primous UI

**What could go wrong.** Corporate Accounting and Treasury have used Primous daily for 8 years. Cloud's UI is different. Even when functionally equivalent, a UI change in the middle of a 12-week migration plus year-end close stress is a recipe for low adoption, manual workarounds, and the kind of "Primous was better" sentiment that makes governance compliance erode. Worst case, a frustrated team stops submitting changes through Cloud and starts emailing the consultant directly.

**How I detect it.** Test environment login data from Week 9 onward. Each business team has 2 to 3 named testers who must run UAT scripts. If their login activity in the test environment is below 3 sessions per tester per week, the resistance signal is real, not a perception problem.

**Contingency.** Dedicated office hours in Weeks 9 to 12, twice weekly, hosted by the consultant in Meridian's space (not over Zoom, where avoidance is too easy). One named change-champion per business team, given direct access to the consultant and the responsibility of being the loudest internal advocate. Post-go-live: 30-minute weekly drop-in for the first 4 weeks, then bi-weekly through Q1 close.

### Risk 4: Governance workflow gap during transition

**What could go wrong.** Cloud's request-review-approve-publish workflow is configured to match Primous's, but the cutover Saturday creates a window where requests in flight in Primous have not yet reached "Publish" while Cloud is going live. A change request approved Friday in Primous might never make it to Cloud, or worse, get re-submitted into Cloud and approved twice.

**How I detect it.** A formal change freeze starting Week 9 closes off non-critical change requests early. The cutover runbook explicitly inventories every in-flight request the morning of cutover, accounts for each one, and either commits it in Primous before the freeze or carries it forward in Cloud post-cutover with a documented audit trail.

**Contingency.** A cutover playbook that includes a "request reconciliation log" signed off by Data Governance lead before either hierarchy goes read-only in Primous. Any requests not accounted for at cutover trigger a hold on the cutover.

### Risk 5: Timeline slip pushes cutover past Week 12

**What could go wrong.** Discovery in Week 1 surfaces something that was not in the assumed scope (custom Primous integration, undocumented validation rule, surprise stakeholder dependency). Without a buffer, even a one-week slip in any phase blows the fiscal close.

**How I detect it.** Weekly status against the W1-12 plan, with a hard checkpoint at end of Week 4 (design sign-off). If the Week 4 milestone slips by more than 3 business days, escalate to Meridian's CIO and consider scope reduction.

**Contingency.** A pre-defined deferral list, agreed with Meridian's CIO at Week 1: PBCS hierarchy view migration is the explicit "deferrable" item. If timeline slips, PBCS continues to consume views from Primous read-only through fiscal close, and the PBCS migration moves to a Q2 phase 2. Corporate Accounting and Treasury workflows do not get deferred. FCCS does not get deferred. Everything else can.

## Section B: Stakeholder Communication and Knowledge Transfer Plan

### Part 1: Stakeholder Communication

#### Corporate Accounting (CoA changes, daily user)

**What they need.** A clear before-and-after of how their daily change request flow looks in EDM Cloud. Specific examples for the most common change types: adding a new account, retiring an account, restructuring a roll-up. The cutover schedule and what they have to do during the change freeze.

**When they need it.**
- Week 5: high-level migration overview, cutover schedule, change-freeze dates.
- Week 9: detailed runbook for their day-to-day flow in Cloud, with screenshots.
- Week 11: hands-on training session.
- Week 12: cutover-day runbook with the on-call number for the consultant.

**Format and channel.**
- Weekly 30-minute live check-in starting Week 5, in Meridian's space, with the team's daily change-makers (not just managers).
- Written runbook delivered as a PDF + searchable internal wiki page. They will use the runbook every day in Q1; format matters.
- Slack channel "edm-migration-corp-acct" for ad-hoc questions, monitored by the consultant team during business hours.

#### Treasury (entity / legal entity changes, lower frequency)

**What they need.** Lower volume of changes, but each change has higher consequences (entity restructuring affects intercompany eliminations and consolidation paths). They need confidence that the workflow is auditable and that nothing gets lost during cutover.

**When they need it.**
- Week 5: overview, cutover schedule, change-freeze dates.
- Week 9: detailed runbook for entity-specific workflows.
- Week 11: training session, focus on entity-specific validations and the IC pair completeness check.

**Format and channel.**
- Bi-weekly 30-minute live check-in starting Week 5 (lower cadence than Corporate Accounting because lower change volume).
- Written runbook delivered as a PDF.
- Direct email channel to the consultant team, since Treasury culture favors written-and-traced communication over Slack.

#### Financial Planning (hierarchy views for PBCS budgeting, read-only consumer)

**What they need.** They are a consumer, not a producer of hierarchy changes. Their need is operational: when the cutover happens, will the views they consume in PBCS still work, and where do they go to find them?

**When they need it.**
- Week 8: written email confirming PBCS view URLs and how to validate them.
- Week 11: 30-minute Q&A session, mostly for reassurance and to surface anything we missed.
- Week 12: cutover-day note confirming the views are live.

**Format and channel.**
- Email and one Q&A session. They do not need weekly check-ins. They need to know it works on cutover day. Anything more is theatre.

### Part 2: Knowledge Transfer Plan

The consultant disengages at end of Week 12. From Week 13 forward, Meridian's internal team owns Cloud operations. Three components.

#### Documentation

- **Configuration design document.** The plan from this engagement, kept as a living document in Meridian's wiki. Source of truth for "why is it like this."
- **Operations runbook.** Day-to-day operations: how to handle a change request, how to debug a failed FCCS sync, how to add a new validation rule, how to restore a property from version history. Delivered as a wiki page with screenshots.
- **Governance manual.** The approval workflow, the role assignments, the escalation paths. Owned by Meridian's data governance lead post-engagement.
- **Integration spec.** REST API endpoints, sync schedules, error-handling contracts with FCCS and PBCS. Owned by Meridian's EPM team post-engagement.
- **Archive retrieval runbook.** How to retrieve and re-load a historical snapshot from cold storage when an audit demands it. Tested at end of Week 12 with the data governance lead.

#### Training

- **Admin training (4 hours).** For Meridian's EPM team. Application configuration, validation rule management, viewpoint structure, integration troubleshooting.
- **Power-user training (2 hours per business team).** For the named change-makers in Corporate Accounting and Treasury. Day-to-day workflows, common edge cases, escalation paths.
- **Governance training (2 hours).** For data governance lead and reviewers. Approval workflow operations, audit log review, request reconciliation.
- **Integration owner training (3 hours).** For whoever owns the FCCS connector going forward. Sync schedules, error handling, manual reconciliation procedures.

All training sessions recorded and stored in the wiki. New hires can re-watch them rather than asking the consultant for re-runs.

#### Readiness confirmation before disengagement

By end of Week 12, before the consultant team leaves:
- A power-user from Corporate Accounting submits, reviews, and commits one change request end-to-end in production, unsupervised. The consultant observes but does not intervene.
- A Treasury power-user does the same on the Entity hierarchy.
- The data governance lead runs a request audit log review unsupervised.
- The EPM team performs one FCCS sync troubleshooting drill (consultant intentionally introduces a benign sync error in test, EPM team finds and fixes it).
- All four readiness checks pass = consultant disengages.

If any readiness check fails, the consultant stays on for an additional 1-week handover at agreed rates. This is in the Statement of Work upfront, not a renegotiation.

## Section C: AI Usage Log

### Interaction 1: Configuration design, single node type vs eight

I asked Claude to draft the EDM Cloud configuration design for Meridian's CoA. The first version proposed eight separate node types, one per CoA segment. I rejected this. The eight segments are dimensions of a single CoA structure, not eight distinct master data categories. Eight node types means eight separate validation rule sets, eight workflow definitions, and eight times the chance for hierarchy drift between segments. I rewrote the design as a single Account node type with the segments expressed as required properties on the same node, which is what FCCS expects to consume and what keeps the governance workflows centralized.

The deeper pattern: AI drafts often optimize for "every entity gets its own type" because that pattern is more general. In domain-specific design, the right question is "what does the downstream consumer expect," and FCCS expects one Account dimension, not eight.

### Interaction 2: Cutover approach, big bang corrected to phased

The first draft of the cutover plan, when I asked Claude to recommend an approach, came back as big bang on cutover Saturday of Week 12. I rejected this. Big bang in a fiscal year-end window is the riskiest possible choice. If something breaks on cutover Saturday, the fiscal close opens two weeks later with a broken metadata source.

I rewrote it as a phased cutover by hierarchy, Entity first in Week 11 with a 4-day soak, CoA in Week 12, then a Week 13 soak before the close opens. The phased approach gives us two cut-points and two soak windows, so a defect in the Entity cutover is detectable and fixable before the CoA cutover happens, and a defect in CoA is detectable before the close opens. The cost is one extra weekend of work; the value is a real contingency window.

The rule I'm watching for: AI drafts optimize for "elegant single-event cutover" because it reads better in a writeup. Real migrations optimize for "detection and rollback windows," which usually means more cut-points, not fewer.

### Interaction 3: Versioning strategy, "migrate everything" rejected

The first version of the versioning strategy proposed migrating all 90+ historical snapshots into EDM Cloud as time-stamped versions, on the rationale that "having everything in one place is operationally simpler." I rejected this for three reasons. First, EDM Cloud is a SaaS product priced on data and activity, and paying ongoing license cost to host six years of cold data that almost nobody reads is wasteful. Second, an SaaS application is not an audit storage system; the right architecture for long-retention regulatory data is immutable cold storage with documented retrieval, not live SaaS. Third, migrating 90 snapshots into Cloud means each one runs through the validation pre-pass and produces exception triage work for legacy nodes that nobody is going to touch anyway.

I rewrote the strategy as: migrate the live version plus the trailing four quarters (covers most-recent close cycles), archive the rest to immutable cold storage with a tested retrieval runbook. The rationale ties to specific financial-services regulatory frameworks (SOX 7-year, SEC 17a-4 6-year, state insurance commissioner requirements) rather than a generic "keep everything" instinct.

The pattern: AI drafts default to maximalist data migration because subtraction is harder than addition. The right answer in regulated industries is almost always tiered storage with documented retrieval, because regulators care about retention and retrievability, not about whether the data lives in the live application.
