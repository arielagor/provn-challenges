# Solution Architecture Brief: Clarion Health Systems

**Prepared by:** Lead Solutions Architect, mpathic.ai
**For:** Dr. Priya Nair (Head of AI Safety), Marcus Chen (ML Platform Lead), Sarah Kim (VP Engineering)
**Purpose:** Prep doc for the technical discovery and solution design session.

## 1. Discovery Plan

### Block 1: Dr. Nair (45 min)

The goal here is to confirm the harm taxonomy and the urgency. We do not want to design a solution against the wrong problem.

- Of the 47 incidents flagged last quarter, what is the breakdown by clinical specialty (mental health, pediatric, substance use, other)? And by harm type (incorrect dosage, missed contraindication, harmful suggestion, scope-of-practice overreach, other)?
- Of the 35 incident growth (12 → 47), how much is real signal vs. better detection? Did your review sample size grow?
- The 3-clinician weekly review samples flagged conversations. What is the sampling rate? What fraction of total flagged conversations actually gets human review today?
- What does the clinical advisory board's "potentially harmful" rating mean operationally? Is it a 1-of-N scale, a binary, or qualitative consensus?
- What would have to be true at the 10-week model release for you to feel confident shipping?

### Block 2: Marcus (60 min, before any group session)

This block is where the deal lives or dies. The questions are designed to surface his framework's actual gaps without asking him to admit gaps.

- Walk me through the architecture of your evaluation framework. Where does a model output enter, what taxonomy does it run against, and where do flags land?
- Of your rules-based taxonomy, which categories were authored before the new specialties (mental health, pediatric, substance use) came into scope? Which were authored after?
- When you see a false negative in production (something the framework rated safe that the clinical board later flagged), what is the typical root cause? Missing rule? Edge case the rule didn't anticipate? Ambiguous output?
- What would a "ground truth dataset" look like to your team? Specifically, what format, what labels, and what cadence would make it usable in your existing pipeline rather than a parallel one?
- Is your framework's strength on the rules side, the orchestration side, or both? Where would external signal genuinely help, if it could?

### Block 3: Sarah Kim (30 min)

Sarah needs to know we won't slow her down. The questions calibrate the launch risk.

- What is the freeze date for the 10-week release, and what is your in-flight regression process between freeze and ship?
- What is your current threshold for "we can ship"? Is it volume of issues, severity, or category-specific?
- What integration changes (if any) are you willing to accept inside the freeze window? What is the line between "augmentation" (acceptable) and "modification" (not)?
- How does your team typically evaluate a vendor in 4 weeks? What proves value?

### Block 4: Clarion ML Platform Engineer (45 min, post-Marcus)

A working session with whoever Marcus assigns as integration owner.

- VPC topology, EKS service mesh, RDS schemas, S3 buckets in scope. What's tagged as PHI?
- IAM model. Who has read access to flagged conversations today? Who would need read access for an mpathic-deployed service?
- Existing observability stack (CloudWatch, Datadog, custom?). What event payload schema does the framework emit?
- Secrets management (AWS Secrets Manager, Vault, other). PrivateLink readiness.
- BAA scope. What does it cover today?

## 2. Proposed Solution Architecture

### Design Principle

mpathic deploys **inside Clarion's VPC, called by Clarion's framework, never replacing it.** Marcus's framework remains the orchestrator. mpathic provides the signal his framework cannot produce internally: clinician-graded evaluations, specialty-specific ground truth, and a continuous learning loop.

### Component Map

```
┌────────────────────── Clarion HIPAA VPC (AWS, us-east-1) ──────────────────────┐
│                                                                                 │
│   Clinical AI ──→  Clarion Eval Framework  ──→  Production Decision            │
│   (EKS pods)        (Marcus's stack)            (response shipped to provider)  │
│                          │                                                      │
│                          │  Selective callout for high-risk categories          │
│                          ▼                                                      │
│              ┌─────────────────────────────┐                                    │
│              │  mpathic Observing Agent    │  Containerized service             │
│              │  (EKS pod, in-VPC)          │  (mpathic-supplied image, ECR)     │
│              │                             │                                    │
│              │  Input:  model I/O          │  Returns:                          │
│              │  Output: structured risk    │  - risk_score (0-1)                │
│              │          score + categories │  - category_flags (PHI-safe)       │
│              │                             │  - rationale (no PHI quotes)       │
│              └─────────────────────────────┘                                    │
│                          │                                                      │
│                          ▼                                                      │
│   Clarion Eval Framework consumes signal, decides flag/route/escalate           │
│                          │                                                      │
│                          ▼                                                      │
│   CloudWatch Logs ──→ S3 (clinical review queue) ──→ Clarion clinician review  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │  PHI-stripped event metadata only
                                     │  (counts, category histograms, latency)
                                     ▼
                          ┌──────────────────────────────┐
                          │  AWS PrivateLink             │
                          │  ↓                           │
                          │  mpathic Studio (managed)    │
                          │  - cross-customer benchmarks │
                          │  - trend dashboards          │
                          │  - alerting on drift         │
                          └──────────────────────────────┘
```

### Where Each mpathic Product Plugs In

**Observing Agent API** runs as a containerized service inside Clarion's VPC. Marcus's framework calls it on a configurable subset of model outputs (we propose: 100% of the three high-risk specialties, sampling on the rest). The Agent returns structured risk signal that flows back through Marcus's pipeline. No model I/O leaves the VPC.

**Clinician-led red teaming** is a one-time engagement followed by quarterly refreshes. mpathic clinicians produce adversarial test cases for the three high-risk specialties. These are delivered as a JSON test corpus that drops into Clarion's existing test harness. Marcus's team owns the integration; mpathic owns the authorship and refresh cadence.

**Human data and benchmarking** happens in two places. (1) A one-time calibration of Clarion's framework against mpathic's ground-truth dataset, producing a precision/recall map of where Clarion's rules are tight, loose, or silent. (2) Ongoing benchmark refreshes scoped to clinical scenarios Clarion adds to their model.

**Ground truth datasets** for the three new specialties are licensed and delivered to Clarion as static, in-VPC training/evaluation assets. They live in Clarion's S3, not ours. They become the answer-key for any future framework iteration Marcus's team builds.

**mpathic Studio** is the only component that needs network access outside the VPC. We solve this with PHI-stripped telemetry over PrivateLink: only category histograms, latency, drift signals, and cross-customer (anonymous) benchmarks. No conversation content. The BAA covers this explicitly. If Clarion's compliance team rejects even PHI-stripped egress, we offer a self-hosted Studio variant deployed in their VPC with reduced cross-customer benchmarking.

### Why This Architecture Beats the In-House Framework Alone

Marcus's framework is sophisticated rules-based detection. It cannot produce its own ground truth, cannot author novel adversarial cases, and cannot calibrate against an external clinical standard. We fill exactly those gaps. The framework gets sharper because of mpathic, not replaced by it.

## 3. Technical Validation Plan (4 Weeks)

The plan is dev/staging-only through Week 3. Production touch is conditional on the Week 4 readout. This is non-negotiable: a production integration in 4 weeks against a HIPAA boundary with a 10-week model release is reckless. The 4-week window proves value; production deployment is a separate, post-POC gate.

### Week 1: Integration Spike

- Deploy Observing Agent as an EKS pod in Clarion's dev VPC. Co-located with Marcus's framework.
- Run 1,000 historical conversations from Clarion's flagged-and-near-miss corpus through both stacks.
- Output: a divergence dataset (where mpathic flagged and Clarion did not, where Clarion flagged and mpathic did not, where they agreed).

### Week 2: Calibration

- mpathic clinical reviewers and Clarion's clinical advisory board jointly review the divergence dataset.
- Produce: precision/recall map of mpathic vs. Clarion's framework on the three high-risk specialties.
- Decision: confirm the categories where mpathic adds genuine signal (vs. noise). These are the categories that go to live shadow in Week 3.

### Week 3: Live Shadow

- mpathic Observing Agent runs in shadow mode in Clarion's dev environment on real (synthetic-PHI) traffic. No enforcement. Every flag is logged but does not affect production decisions.
- mpathic Studio (PrivateLink-mode) populates with PHI-stripped telemetry.
- Output: live divergence cases, p99 latency under realistic load, false-positive rate at production traffic shapes.

### Week 4: Readout and Decision Gate

- Joint readout to Nair, Marcus, Sarah, and a CMO's office representative.
- Success metrics presented:
  - **Detection uplift:** % of clinician-confirmed harmful instances mpathic caught that Clarion's framework missed. Target: ≥30% incremental detection on the three high-risk specialties.
  - **False-positive ceiling:** mpathic FP rate on Clarion's traffic. Target: ≤5% at the agreed threshold.
  - **Latency:** p99 under shadow. Target: ≤200ms added to evaluation pipeline.
  - **Integration burden:** lines of Marcus's framework that had to change. Target: <500 lines, contained to a single integration module.
- Decision: green-light production rollout (Weeks 5–8), phased to be live before the 10-week model freeze.

### Why This Maps to Advancing the Deal

Marcus needs proof his framework is augmented, not replaced. The Week 1 divergence dataset gives him that proof. Sarah needs to know we won't blow the launch. Dev/staging-only through Week 3 + Week 4 decision gate gives her that. Nair needs the harm-reduction story. The Week 4 detection-uplift metric tied to the three specialties gives her that. The CMO's office signs once Marcus + Sarah + Nair are aligned.

The 4-week structure deliberately produces a yes/no decision before the model release freeze, with a credible production rollout window if the answer is yes.
