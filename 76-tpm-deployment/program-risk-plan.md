# Program & Risk Plan: mpathic Observing Agent Deployment, 5 Sites, 90 Days

**Senior TPM:** Ariel Agor
**Client:** Fortune 50 pharma (anonymized)
**Program:** Observing Agent API deployment across 5 clinical trial sites in 3 jurisdictions
**Document scope:** Phased plan, critical path, jurisdiction-specific compliance gates, risk register, go-live delay decision.

## 1. Go-Live Delay Decision (US Site 1)

**Recommendation: HOLD.** 48 to 72 hour diagnostic window before re-evaluating.

### Reasoning

The reported issue is inconsistent participant identifiers from the client's EDC across API calls. That is not a cosmetic bug. Three regulatory and clinical implications make this a hold:

1. **Adverse event signal routing.** Observing Agent flags get attached to a participant ID. If the ID is unstable across calls, a flag generated at minute zero may not associate with the correct participant record by minute thirty. In a clinical trial monitoring deployment, that is a missed safety signal. The whole point of the Observing Agent is to catch these in time.
2. **Audit trail integrity.** HIPAA, GxP, and the FDA's 21 CFR Part 11 all require attributability and integrity of records. A non-stable participant identifier breaks attributability. A regulator auditing this deployment in 18 months will ask "show me how you reliably linked monitoring outputs to participants on day one." Without a clean ID layer, that question has no good answer.
3. **Pilot-to-production transition risk.** The contract specifies no acceptable gap in clinical oversight. Going live with a known data integrity issue is the opposite of clinical oversight. The right move is to extend pilot oversight by 2 to 3 days, not compress validation.

### Conditions to proceed

We re-evaluate at 48 hours. We proceed only when all of the following are true:

- Root cause identified and documented (configuration vs. pipeline bug)
- Fix deployed in test environment, verified on a corpus of at least 500 historical participant interactions
- Engineering lead AND clinical science annotation lead jointly sign off that monitoring accuracy is unchanged on the test corpus post-fix
- Client confirms the fix path on their EDC side does not require recertification of their data pipeline

If any of those conditions is not met at 72 hours, we extend hold and replan downstream sites with the new floor.

### Client communication within the next 2 hours

A short call with the client's clinical operations PM. Not email. The framing:

> "Our pre-go-live integration testing flagged inconsistent participant identifiers from the EDC across API calls. We do not yet know if this is a config issue on our side or a data pipeline issue on yours. We are holding US Site 1 go-live by 48 to 72 hours while we diagnose. The reason we are not pushing through this is participant ID integrity is what makes adverse event detection work. Going live with this unresolved would mean we cannot reliably route safety signals to the correct participant, which is the entire point of this deployment.
>
> What we need from your side in the next 24 hours is access to your EDC integration team so our engineering lead can compare API responses against your data pipeline. What you can tell your VP of Clinical Operations is that we caught this before go-live, not after, which is the system working as intended.
>
> I will send a written summary within 4 hours and we will reconvene at 24 hours with a diagnosis and a decision."

Followed by a written summary to the client PM and CC to the VP of Clinical Operations within 4 hours. No PR-spin language. Plain factual update.

## 2. Phased Deployment Plan

### Sequencing logic

The five sites are not identical parallel deployments. They differ in jurisdiction, language, regulatory regime, and integration shape. Sequencing reflects the risk and learning curve.

**Phase 1 (Days 1 to 30): US Site 1.** Single-site pilot in the US. HIPAA and SOC 2 Type II requirements are mpathic's home turf. Use this site to debug the integration, lock down deployment runbook, validate monitoring accuracy on production traffic shape. Lessons compound to all other sites.

**Phase 2 (Days 25 to 50): US Site 2.** Begins overlapping with the tail of Phase 1. Same jurisdiction, same compliance regime, smaller integration surface. Confirms the runbook is repeatable.

**Phase 3 (Days 40 to 70): UK Site.** First international site. Adds UK GDPR and NHS data governance. Different data residency requirements (EU/UK), different DPA scope. Begins after US runbook is proven so we are not debugging integration AND jurisdiction at the same time.

**Phase 4 (Days 55 to 90): Germany Sites 1 and 2 in parallel.** Both EU GDPR. Both require Data Protection Impact Assessments. Engineering capacity is the binding constraint by this point, so we start them only after UK runbook is fielded. They are partially parallel because the DPIA work and language localization can run in parallel, but the integration testing windows are staggered to avoid colliding on engineering review.

### Why not start Germany earlier in parallel

Two reasons. First, DPIAs are the longest pole in the EU (typically 4 to 6 weeks of legal and DPO review on the client side). Starting them on day 1 means they finish before our engineering team is ready to act on them. Second, the German sites are higher complexity due to EU GDPR's strict data minimization and right-to-erasure requirements that interact with clinical trial retention obligations. They benefit from the runbook lessons of Sites 1 to 3.

### Critical path

The dependency chain (longest path from contract execution to all-five-sites live):

1. Contract execution (Day 0)
2. mpathic platform configuration for client tenancy and EDC integration spec (Days 1 to 10)
3. **US Site 1 EDC integration debug and resolution of the participant ID issue (Days 10 to 14, after the hold)**
4. US Site 1 clinical science annotation protocol sign-off (Days 12 to 18, runs parallel to integration debug)
5. US Site 1 go-live and 7-day stability watch (Days 18 to 25)
6. Runbook freeze for US deployment pattern (Day 25)
7. UK DPIA and NHS data governance review on client side (Days 15 to 50, runs parallel)
8. UK Site go-live (Day 60)
9. Germany DPIAs and DPO review (Days 30 to 65, runs parallel)
10. Germany Site 1 go-live (Day 75), Germany Site 2 go-live (Day 85)

The critical path runs through US Site 1 stability watch (because that is where the runbook gets proven) and through Germany DPIA completion (because EU regulatory review is the longest external dependency).

## 3. Site-Specific Compliance Gates

### US Site 1 and US Site 2

Sign-off required before go-live:
- HIPAA BAA executed between mpathic and client
- SOC 2 Type II evidence package shared with client InfoSec
- Risk Assessment (HIPAA Security Rule 164.308) covering Observing Agent's PHI handling
- Audit logging confirmed live (164.312(b))
- Participant ID integration verified against EDC (this is what triggered the US Site 1 hold)
- Clinical science team sign-off on annotation protocol coverage for US English clinical vocabulary

### UK Site

Sign-off required before go-live:
- UK GDPR Data Processing Agreement executed
- NHS Data Security and Protection Toolkit alignment confirmed (if NHS data is in scope)
- Data residency verified (UK or EU/UK adequacy region)
- Records of Processing Activity updated to include this deployment
- Right-to-erasure operational procedure documented (interaction with clinical trial retention)
- Clinical science team sign-off on annotation protocol coverage for UK English clinical vocabulary, including NHS-specific terminology
- Pseudonymization scheme reviewed and accepted by client DPO

### Germany Sites 1 and 2

Sign-off required before go-live:
- EU GDPR Data Processing Agreement executed
- Data Protection Impact Assessment completed and accepted by client DPO
- Joint controller analysis if Observing Agent's outputs constitute joint processing (typical answer: processor only, but documented)
- Article 28 GDPR processor obligations documented
- Data residency verified (EU)
- Right-to-erasure procedure documented including interaction with §40 AMG (German Medicines Act) trial retention
- Clinical science team sign-off on annotation protocol coverage for German clinical vocabulary
- Works council notification if applicable (BetrVG §87 if monitoring extends to clinical staff conduct, which it does not, but documented)

The pattern: HIPAA gates are about administrative safeguards and audit logging. UK GDPR gates add data residency and pseudonymization. EU/Germany GDPR gates add the DPIA and explicit Article 28 processor documentation, plus the German trial retention interaction.

## 4. Risk Register

| # | Risk | Probability | Impact | Owner | Mitigation |
|---|------|-------------|--------|-------|-----------|
| 1 | EDC participant ID issue does not resolve in 72 hours, US Site 1 holds longer | Medium | High (slips program 1 to 2 weeks) | Engineering Lead | Joint debug session with client EDC team within 24h; if root cause is on client side, escalate to client CTO via mpathic CEO relationship; have a fallback ID-stabilization layer designed in mpathic stack as a worst-case bridge |
| 2 | Germany DPIA review takes 8+ weeks instead of 4 to 6 | Medium | High (delays Germany sites past day 90) | Client DPO + mpathic Privacy Lead | Start DPIA on day 1 in parallel; weekly status check with client DPO; pre-prepare DPIA template based on a HIPAA + UK GDPR analog so client DPO is reviewing a draft, not authoring from blank |
| 3 | Clinical science annotation team capacity is consumed by another release and slips US Site 1 protocol sign-off | Medium | Medium (delays US Site 1 by 1 week) | VP Clinical Science (mpathic) + Senior TPM (this role) | Lock annotation lead's calendar for the deployment window in week 1; produce a "minimum coverage" protocol that can ship US Site 1 with a documented expansion path for Sites 2 to 5; weekly sync between TPM and clinical science lead |
| 4 | Client clinical operations PM cannot keep up with multi-site coordination given AI safety vendor inexperience | High | Medium (slows decision velocity, creates miscommunication) | Senior TPM (this role) | Establish a 2-page-max written brief format for every client-facing update; offer a 30-min weekly coaching session with their PM to translate technical status into client-language; copy their VP of Clinical Operations on every update so escalation path is always one hop |
| 5 | A monitoring accuracy regression is discovered post-go-live at one site and triggers a regulatory notification requirement | Low | Severe (clinical trial pause, regulatory event) | CTO + Senior TPM | Pre-define accuracy SLA in the contract (e.g., recall on adverse event categories); pre-define notification thresholds with client clinical safety officer; rehearse the notification chain in a tabletop exercise before US Site 1 go-live |
| 6 | (Non-technical) CEO-VP Clinical Operations relationship gets ahead of the operational reality and a commitment is made that the four-person engineering team cannot meet | Medium | Medium (relationship damage + scope creep) | Senior TPM (this role) + CEO | Weekly 15-minute "executive readout" prep call between TPM and CEO so the CEO has the operational picture before any client conversation; written commitment ledger so the TPM can flag scope drift early |

## 5. What I'm Watching

Three early warning signals over the next 14 days:

- **EDC integration diagnostic velocity.** If the client's integration team does not engage in the first 24 hours, the hold extends. The client's responsiveness here is a leading indicator for the rest of the program.
- **DPIA template progress on the EU side.** If the client DPO has not opened the DPIA template by day 14, Germany goes from medium to high probability of slipping past day 90.
- **Clinical science team sign-off cadence on US Site 1 protocol.** If protocol sign-off slips past day 18, the runbook freeze slips, and every downstream site moves with it.

These three signals get reported in the weekly status writeup and escalated by exception, not on schedule.
