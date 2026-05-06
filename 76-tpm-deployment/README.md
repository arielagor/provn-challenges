# Senior TPM Submission: mpathic Multi-Site AI Safety Deployment

**Author:** Ariel Agor
**Role applied:** Senior Technical Program Manager (TPM), AI Safety, Human Data

## Section A: Stakeholder Communication Framework

### Internal coordination cadence

Three communities are involved on mpathic's side: engineering, clinical science, customer success. None of them report to me. The cadence is built around getting decisions out of the right room at the right time.

**Daily standup, 15 minutes, asynchronous Slack thread.** Engineering lead, clinical science annotation lead, customer success lead, and me. Three prompts: what shipped yesterday, what is at risk today, what decision do you need from someone else this week. The point is not status. The point is to surface unowned decisions before they become blockers.

**Weekly 30-minute live sync.** Same four people. Walk the dependency tracker for the next two weeks. Identify cross-team handoffs that need rehearsal. The TPM owns this meeting and the dependency tracker.

**Bi-weekly clinical science alignment, 60 minutes.** This is where the annotation protocol decisions get made. I am present, the engineering lead is present, but the clinical science VP runs the agenda. My job here is to translate the engineering constraints (latency budget, compute cost, audit logging requirements) into language the clinical science team can incorporate into protocol decisions, and to translate their accuracy thresholds back into engineering acceptance tests.

**Bi-weekly executive readout, 30 minutes.** CTO, CEO, me. One-page written brief sent 24 hours in advance. The agenda is decisions needed, not status. I do not bring the CEO problems without options.

### Client-facing updates

The client has a clinical operations PM with no AI safety vendor experience and a VP of Clinical Operations who is the executive sponsor on their side. The cadence is built for the PM but the VP is always on the cc line so escalation is one hop.

**Weekly written status, every Friday by noon ET, capped at two pages.** Format is locked: (1) what shipped this week, (2) what is at risk, (3) decisions needed from the client this week, (4) jurisdiction-specific compliance status, (5) one paragraph in plain English on what the AI is and is not doing differently than last week. The plain-English paragraph is not optional. It is the part that lets the client PM brief their VP without translation.

**Weekly 30-minute live call, every Tuesday.** Client PM and me. Walk last week's status doc, surface anything that did not fit on two pages.

**Monthly 60-minute executive call.** Their VP Clinical Operations, our CEO, me. Strategic, not operational. I prepare the materials.

**Ad-hoc briefings as needed.** Defined in the escalation protocol below.

### Escalation protocol

Specific thresholds, not generic levels.

**Threshold 1: I notify the client PM same business day.**
- Schedule slip on any site of more than 3 business days
- Any change to a compliance gate
- Any monitoring accuracy delta of more than 2% on a deployed site
- Any engineering team capacity change (someone leaving, extended absence)

**Threshold 2: I notify the client PM AND copy their VP within 4 hours.**
- Discovery of a data integrity issue affecting deployed sites (the EDC participant ID issue is exactly this, except it was caught pre-go-live)
- Any P1 or P0 incident
- Any regulatory notification trigger
- Any CEO-level commitment that needs validating against operational reality

**Threshold 3: I escalate internally to CTO + CEO within 1 hour, before any client comm.**
- P0 incident at a deployed site
- Discovery of a compliance gap that may already have produced a notification-eligible event
- Any signal that a regulator may already be aware of a problem before we are

The principle: the client gets faster notification on operational issues, slower notification on issues that need internal coordination first. Never let the client find out from a regulator before they find out from us.

### How to deliver bad news to a client without prior AI safety vendor experience

Three rules, learned the hard way on every prior vendor relationship.

**Rule one: lead with the user impact, not the technical cause.** "We are holding US Site 1 go-live by 48 hours" is the lead. "Inconsistent participant identifiers from the EDC" is the second sentence. The PM needs to brief their VP within 30 minutes of my call. They cannot do that if I lead with a technical detail they have to look up.

**Rule two: name what is decided and what is still being investigated.** "We have decided to hold. We have not yet decided whether the root cause is on our side or yours. We will know within 48 hours." The PM can speak with confidence about the parts I have decided. They can defer the parts I am still investigating without losing trust.

**Rule three: end every bad-news call with what they need to do in the next 24 hours.** Not "we will keep you posted." A specific ask. "Get me access to your EDC integration team in the next 24 hours." That gives the PM something to do. People with no prior vendor experience handle bad news better when they have an action item.

The unspoken rule: never let a bad-news email be the first the VP hears of it. The PM gets the call. The VP gets a written summary within 4 hours. The order matters.

## Section B: Incident Response Plan

### What constitutes an incident in this deployment

An incident is any event where Observing Agent's monitoring of clinical trial conversations is degraded, broken, or producing misleading output, OR any event where the audit trail or compliance posture of the system is compromised.

Three categories:
- **Monitoring incidents:** the system is missing safety signals it should catch, or generating false flags at a rate above SLA, or experiencing latency that prevents real-time review.
- **Data incidents:** participant IDs misalign, audit logs lose attributability, data residency is violated, PHI flows where it should not.
- **Compliance incidents:** a regulatory requirement is not being met, or a process breakdown means we cannot prove it is being met.

### Severity tiers

**P0: Critical.** Live monitoring is broken or producing systematically incorrect output at a deployed site. Or a confirmed compliance breach (PHI egress, audit log gap, data residency violation).

- **Detection-to-acknowledgment SLA:** 15 minutes (24/7)
- **Detection-to-mitigation SLA:** 1 hour (mitigation = either fix, or take system offline at the affected site with manual oversight bridge)
- **Detection-to-resolution SLA:** 24 hours
- **Notification chain:** mpathic on-call engineer → engineering lead → CTO → Senior TPM → CEO → client PM → client VP. CEO and client PM are notified in parallel within 30 minutes. CTO authorizes the mitigation decision.
- **Resolution ownership:** Engineering lead owns root cause and fix. TPM owns coordination, comms, and the post-incident review.

**P1: High.** Monitoring accuracy is measurably degraded but the system is still running. Or a single-site data anomaly that has not yet propagated. Or a near-miss compliance event.

- **Detection-to-acknowledgment SLA:** 1 hour (business hours), 4 hours (off-hours)
- **Detection-to-mitigation SLA:** 4 hours
- **Detection-to-resolution SLA:** 72 hours
- **Notification chain:** Engineering lead → CTO → TPM. Client PM notified within 4 hours by TPM. Client VP cc'd. CEO informed via the executive readout, not paged.
- **Resolution ownership:** Engineering lead.

**P2: Medium.** A degradation that does not affect monitoring quality at deployed sites but signals risk (e.g., elevated error rate in non-critical pathway, capacity headroom shrinking, a non-blocking compliance documentation gap).

- **Detection-to-acknowledgment SLA:** 1 business day
- **Detection-to-resolution SLA:** 2 weeks
- **Notification chain:** Engineering lead → TPM. Logged in incident registry. Reported in weekly status.
- **Resolution ownership:** Engineering lead.

### When monitoring accuracy degradation becomes a regulatory notification requirement

This is jurisdiction-specific. The general rule: any sustained degradation that means the system cannot reliably detect adverse event signals during a clinical trial monitoring window crosses into regulatory territory.

**US (HIPAA + GxP):** Not a HIPAA notification by itself unless PHI was involved. But the FDA's 21 CFR Part 312 (IND Safety Reporting) requires the trial sponsor to report adverse events within specified timelines. If our monitoring failure means an adverse event was not detected and reported, the sponsor (the pharma company) has a notification obligation. Our internal trigger: any P0 lasting more than 4 hours on a deployed clinical trial site.

**UK (UK GDPR + MHRA):** UK GDPR has a 72-hour breach notification window. MHRA reporting follows the same 21 CFR-equivalent timelines via UK regulations. Our internal trigger is the same as US: P0 lasting more than 4 hours.

**Germany (EU GDPR + BfArM/PEI):** EU GDPR Article 33 has the same 72-hour breach notification. German pharmacovigilance reporting via BfArM or PEI follows EU clinical trial regulation. Our trigger remains the same.

The decision tree at the moment of incident: (1) is PHI compromised? (2) was a clinical trial safety signal missed? (3) is the audit trail intact? Any "yes" to (2) on a deployed site triggers a sponsor notification meeting within 24 hours. We do not unilaterally notify regulators; the sponsor does. Our job is to make sure the sponsor has what they need to make that call.

### Post-incident review for this client

Standard post-incident review at 5 to 10 business days post-resolution, plus two additions specific to this engagement.

**Standard:** what happened, what was the contributing chain, what changed, what we are doing to prevent recurrence, action items with owners.

**Addition 1: Joint review with client clinical operations.** This client has no prior AI safety vendor experience. The post-incident review is also a teaching moment for the client PM. We co-author the writeup so they understand the system better at the end of every incident than at the start. Over time this builds their fluency and reduces the cost of future incidents.

**Addition 2: Regulatory readiness check.** Does the post-incident artifact stand up to a regulator's "show me what happened" request 18 months from now? If the writeup would not survive that question, it is not done.

## Section C: AI Usage Log

### Interaction 1: Risk register, generic vs. specific

I asked Claude to draft the risk register. The first version had risks like "Compliance issues may delay deployment" and "Engineering capacity may be insufficient." Both true. Both useless.

I rewrote each risk to be specific enough to act on. "Compliance issues may delay deployment" became "Germany DPIA review takes 8+ weeks instead of 4 to 6." That is testable, has a probability anchor, and points at a specific mitigation (start the DPIA on day 1, give the client DPO a draft). I also added the non-technical risk explicitly because the spec called for one and the first draft did not have one. Risk #6, the CEO-VP Clinical Operations relationship overcommitting to the four-person engineering team, is the kind of risk that AI drafts skip because it is awkward to name a risk that involves the CEO. It is also the kind of risk that breaks programs.

### Interaction 2: Go-live decision framing

The first draft of my go-live decision, when I asked Claude to help structure it, came back as a balanced "could go either way" analysis. Lists of pros, lists of cons, ending with "the TPM should weigh these factors."

The spec specifically says the CTO expects me to bring a recommendation, not a question. The first draft was a question dressed as analysis. I rewrote the section to lead with HOLD as the explicit recommendation, then the three regulatory and clinical reasons, then the conditions to proceed, then the client comm. The structure puts the decision first because the CTO and the client VP both need the decision before the rationale. They will read the rationale only if they want to challenge it.

The deeper pattern: AI drafts default to balanced framing because balanced framing is the safer mode. In a TPM role, balanced framing on a go-live decision is exactly the wrong move. The CTO needs me to take a position. I rewrite for that.

### Interaction 3: Incident severity tiers

The first draft of P0/P1/P2 had generic SLAs (15 min, 4 hours, 1 day). I kept the SLAs but added something the first draft was missing: which jurisdiction-specific regulatory notification each tier could trigger. The first draft treated the severity tiers as a generic engineering construct. In a clinical trial deployment, the severity tier is also the input to a regulatory decision. P0 lasting more than 4 hours on a deployed site triggers a sponsor notification meeting within 24 hours. That language is mine, not Claude's.

The second thing the first draft missed: who notifies whom in what order. Generic incident response plans say "notify stakeholders." I rewrote to specify that the CEO and client PM are notified in parallel within 30 minutes for P0, but the CTO authorizes the mitigation. The order of those calls matters because the wrong sequence makes it look like the CEO was caught off guard by the client. That is a relationship management rule, not an engineering rule, and the AI draft did not have it.
