# Clarion Health Systems: Lead SA Submission

**Author:** Ariel Agor
**Role applied:** Lead Solutions Architect, mpathic.ai

## Section A: Deal Strategy & Stakeholder Navigation

### Bringing Marcus from cautious to supportive

Marcus's resistance is not really about mpathic. It is about a 14-month investment from his team that he is being asked to put alongside a vendor. If we start the conversation with mpathic's product, we lose. We start with his framework.

The first 1:1 with Marcus is structured as a working session on his framework. I ask him to walk me through it. I do not show slides. I ask, specifically, where it has the rules he wishes someone else had authored, where the false negatives keep coming from, and what a useful external signal would look like in his pipeline. He will name gaps. Every framework has them.

Then I reframe mpathic. We are not the orchestrator. He is. Our Observing Agent gets called by his framework, returns structured signal, and his framework decides what to do with it. He stays in the architecture diagram as the central component. Our ground-truth datasets and adversarial corpora get delivered to him as static assets that drop into his test harness. Public co-authorship of the integration writeup and a joint conference talk are on the table once we get to deployment.

The frame I want him to leave with: "This vendor adds the data layer my team can't produce internally and wouldn't want to. They make my framework sharper. The integration is a module I own."

### Handling the "in-house framework already covers this" objection

I do not refute it. I affirm it.

The objection is mostly true. Their framework does cover their needs as those needs were defined when the framework was authored. The 47-from-12 incident growth is the evidence that the surface area has changed faster than the rules have. New specialties (mental health, pediatric, substance use) have failure modes that rules-based taxonomies are slow to catch because the failure mode is often ambiguity, scope-overreach, or absence of an answer rather than a wrong answer.

The reframe is: rules-based detection scales linearly with rule authorship. AI safety scales superlinearly with model surface area. The gap is closing the wrong way. mpathic provides the parts a rules engine structurally cannot: clinician-graded ground truth and continuously refreshed adversarial corpora. That is not a competitive claim. It is a labor and authorship claim.

### Recommended sequence of stakeholder engagements

1. **Dr. Nair, 1:1 (week 0).** Re-confirm urgency, harm taxonomy, and the model-release decision criteria. This is free signal and frames every later conversation.
2. **Marcus, 1:1 (week 0).** Working session on his framework. Surface gaps. Plant augmentation framing. Get him to a "yes to a workshop" by end of meeting.
3. **Joint Marcus + Nair architecture workshop (week 1).** Co-design the integration on a whiteboard. Marcus drives. mpathic SA writes up afterwards. Marcus's name is on the writeup.
4. **Sarah Kim readout (week 1, after the workshop).** Marcus presents the integration plan. I am there to back the timeline credibility and the shadow-mode-first design. Sarah's enthusiasm depends on Marcus's signal, so Marcus is the messenger.
5. **CMO's office (week 2).** Nair sponsors. ROI is framed as clinician-hours-saved-from-manual-review plus harm-prevention. SA provides the architecture-on-one-page. AE owns commercials.
6. **POC kickoff (week 2).** Marcus owns integration. Nair owns clinical review of divergence data. Sarah gets weekly status. mpathic SA runs the joint readouts.

The sequencing principle: Marcus is the highest-risk stakeholder and Sarah is the most influenced by Marcus's signal. So Marcus has to be turned before Sarah is brought in. Nair is leveraged early to keep urgency hot, and again at the CMO conversation to convert technical confidence into budget.

## Section B: SA Function Playbook Extract

### Repeatable assets from this engagement

**HIPAA + VPC reference architecture.** A canonical diagram of how mpathic deploys inside a customer's HIPAA-compliant AWS VPC, with PrivateLink, BAA scope, and explicit data-flow boundaries. Reused across every healthcare prospect with substantially the same compliance posture.

**Augmentation pattern catalog.** Patterns showing how Observing Agent integrates as a callout from an existing customer-built evaluation framework, with code-level contract examples (request/response schemas, error handling, fallback when mpathic is unavailable). The "augment, don't replace" story becomes a 30-second concrete answer rather than a marketing claim.

**4-week POC blueprint with measurable gates.** Week-by-week structure with go/no-go decision gates, shadow-mode-only-through-week-3, success metrics tied to clinically meaningful outcomes (detection uplift, FP rate, p99 latency, integration burden). Becomes the default first-touch validation pitch.

**Specialty-coverage map.** Per-specialty (mental health, pediatric, substance use, oncology, primary care, etc.) ground-truth dataset descriptions, adversarial corpus sizes, clinician-reviewer credentials, and refresh cadence. Lets the SA + AE quickly answer "do you cover X?" without going back to product.

**ROI calculator.** Two-input model: clinician-hours saved on manual review (replaces N hours/week of clinician time at $X loaded cost) plus a harm-prevention component (avoided incidents at $Y per harm event, with conservative anchors). Used in CMO/CFO conversations.

**Battlecard against the "we built it ourselves" objection.** Includes the rules-engine-vs-ground-truth framing from Section A, plus three patterns of how internal frameworks fail at scale that mpathic specifically addresses.

### SA engagement model by stage

**Pre-discovery.** SA reviews the AE's qualifying notes. Pulls the customer's public technical posts (engineering blog, conference talks). Drafts a hypothesis-loaded discovery doc with stakeholder-specific question blocks. AE owns the meeting setup; SA owns the technical narrative going in.

**Discovery.** SA is on every technical call. AE leads commercial framing and stakeholder management. SA writes the post-call architecture sketch within 24 hours and circulates internally. SA drives any working-session agenda.

**Solution design.** SA owns. Customer's senior engineer is co-author of the architecture document. AE is informed but not in the working sessions unless commercial questions surface. The deliverable is the architecture diagram + integration patterns + risks/trade-offs document.

**POC scoping.** SA owns the technical plan (week-by-week structure, success metrics, integration ownership). AE owns the commercial wrapper (POC contract, success-criteria-to-paid-pilot ladder). Joint readouts to the customer.

**POC execution.** SA runs weekly checkpoints with the customer's integration owner. Surfaces blockers. Owns escalation to mpathic Engineering. AE handles any commercial drift (scope creep, timeline slip).

**Close partnership.** SA is on the technical sign-off conversations. AE owns commercials. SA explicitly does not own pricing.

**Expansion design.** Post-deal, SA owns the architecture review for any net-new module the customer wants to add. AE owns the renewal and the pricing conversation.

### First asset I would build

The HIPAA + VPC reference architecture diagram, with the augmentation pattern (Observing Agent as a callout from a customer-built framework) baked in.

Why first: it removes the two largest deal-killers in this segment in a single artifact. Every healthcare AI safety prospect mpathic talks to will ask "can you stay in our VPC?" and "won't you replace what we built?" The reference architecture answers both in 30 seconds, makes the answer concrete enough that a customer's senior engineer can stress-test it on the spot, and turns what would otherwise be a multi-meeting trust-building exercise into a single working session. It is also the asset that compounds the fastest: every customer engagement adds annotations, edge cases, and integration variations back into the canonical diagram.

The next two assets, in order, are the 4-week POC blueprint and the specialty-coverage map.

## Section C: AI Usage Log

### Interaction 1: Replace-not-augment architecture, rejected

I asked Claude to draft a first-cut architecture diagram for mpathic integrated into Clarion's stack. The first draft put the Observing Agent in front of Clarion's framework, intercepting model output before Marcus's framework saw it. I rejected this hard. It positions mpathic as a replacement for the rules engine, which is exactly the framing that kills the deal per the spec's "augment, don't replace" constraint and per Marcus's known posture. I redrew it with Marcus's framework as the orchestrator and Observing Agent as a callout from inside the framework. Marcus owns the request/response contract; mpathic provides the signal. The architecture diagram in the brief reflects this.

The deeper lesson: when a draft optimizes for "show the vendor's product clearly," it tends to centralize the vendor in the diagram. In a deal where the customer's existing investment has to stay central, the vendor has to be willing to be drawn small. Claude's first draft was too vendor-centric. I drew mpathic smaller.

### Interaction 2: Stakeholder sequencing, reordered

I asked Claude to draft the recommended stakeholder engagement sequence. The first draft was Marcus first, then Sarah, then CMO, with Nair as a continuous champion in parallel. I changed it. Nair goes first, she is free signal and reframes urgency for everything that follows. Marcus goes second because his resistance is the deal-killer. Sarah goes third, after Marcus has been turned, because Sarah's enthusiasm is downstream of Marcus's technical signal. CMO goes last with Nair sponsoring and Marcus + Sarah's technical sign-off in hand.

The reason I rejected the first draft: it treated stakeholder sequencing as a linear progression by hierarchy rather than as risk management. Marcus is not just a step; he is the deal-killer if not turned, so the entire sequence is built backward from "what does Marcus need to see to say yes." The Section A sequence in the README reflects this.

### Interaction 3: 4-week POC scope, restructured

I asked Claude to draft the 4-week technical validation plan. The first draft proposed a full production integration over 4 weeks, Observing Agent live in production by Week 4, with 70% of model outputs routing through it. I rejected this. Production touch in 4 weeks against a HIPAA boundary with a 10-week model release on the line is the kind of plan that reads bold in a brief and ends careers in a postmortem.

I restructured to dev/staging-only through Week 3, with Week 4 as a decision gate (not a deployment). Production rollout is a phase 2 that we earn the right to propose only after Week 4's metrics are presented. This explicitly de-risks Sarah's launch concern, which the original draft did not. The architecture brief's Section 3 reflects the restructured plan.

The pattern across all three interactions: Claude defaults to drafts that look strong on paper. My job as the SA is to read every draft against the customer's actual risk posture and rewrite the parts that look strong but would fail the room.
