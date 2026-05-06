# Migration & Configuration Plan: Meridian Financial Group

**Engagement:** On-premise Oracle EDM (Primous) to Oracle EDM Cloud
**Lead consultant:** Ariel Agor
**Timeline:** 12 weeks, no slippage past Week 12 (Fiscal year-end close opens Week 14)

## 1. EDM Cloud Configuration Design

### Application choice and structure

Two separate Oracle EDM Cloud applications, not one combined.

- **Application 1: Planning template, dimension type "Account."** Hosts the Chart of Accounts hierarchy. The Planning application template is the right base because Meridian's CoA feeds both FCCS (consolidation) and PBCS (planning). Planning's dimension semantics line up with what PBCS expects, and the FCCS connector handles the account-to-FCCS-member mapping at sync time.
- **Application 2: FCCS template, dimension type "Entity."** Hosts the legal entity hierarchy. FCCS's application template ships with FCCS-specific validations baked in (currency, intercompany, account type at entity level), which we want enforced at the source rather than discovered during a close cycle.

### Node types

For the Chart of Accounts hierarchy (8 segments, 4,200 nodes), I am proposing a **single node type with property-based segmentation**, not eight separate node types. Rationale: the segments are dimensions of a single CoA structure, not distinct master data categories. A single "Account" node type with the 8 segments expressed as required properties is what FCCS expects to consume, keeps the validation rules centralized, and avoids a 8x multiplication of approval workflows.

Properties on the Account node type:
- Segment 1 to 8 values (with reference data per segment)
- Account Type (Asset, Liability, Equity, Revenue, Expense), required, validated
- Balance Type (Debit, Credit), required, validated against Account Type
- Currency Code
- Active Flag
- Statutory vs Management indicator (drives which alternate viewpoint a node appears in)
- FCCS Member Mapping (the FCCS-side member name when names diverge)
- Effective Start / End dates
- Owner (governance attribution)

For the Entity hierarchy (320 entities across 12 countries), a single "Entity" node type with country, currency, intercompany pair, and tax-jurisdiction properties.

### Views and viewpoints

Two viewpoints on top of the CoA Account node type:
1. **Statutory view** (the GAAP / IFRS reporting hierarchy used by FCCS for consolidation)
2. **Management view** (the management reporting hierarchy used by PBCS for budgeting)

Two viewpoints on top of the Entity node type:
1. **Legal Entity view** (the consolidation hierarchy)
2. **Geographic view** (regional roll-up used by management reporting)

Both Statutory and Management viewpoints share the same underlying nodes, so a node added once is visible in both views with viewpoint-specific parent assignments. This is a meaningful improvement over Primous, where alternate hierarchies tended to drift because they were maintained as parallel structures rather than as views over a single source.

### Validation rules

Configured as Cloud-native validations, not custom scripts.

- **Account Type to Balance Type consistency.** Asset and Expense accounts must be Debit. Liability, Equity, and Revenue must be Credit. Hard fail on commit.
- **Leaf-only posting.** Only leaf nodes can have a Balance Type. Parent nodes must be roll-ups. Hard fail.
- **FCCS member name conformance.** The FCCS Member Mapping property must conform to FCCS's character set (no spaces in member names, length cap). Hard fail. This catches the most common cause of failed FCCS metadata loads.
- **Intercompany pair completeness.** If a node is flagged as intercompany, its IC pair entity must exist and be active. Soft fail (warning) at request submit, hard fail at commit.
- **Effective-date overlap check.** Start and end dates cannot overlap conflicting versions of the same node. Hard fail.
- **Cross-viewpoint consistency.** A node's Account Type cannot differ between Statutory and Management viewpoints. Hard fail.

### Governance controls baked into the configuration

Three approval layers in the request workflow:
1. **Author submits the request.** System validates against the rules above. Validation fail blocks submission.
2. **Domain reviewer approves** (Corporate Accounting for CoA, Treasury for Entity). The reviewer is determined by the node type, not assigned per request.
3. **Data Governance approves** (final commit gate). All requests, regardless of size.

This 3-step Request → Review → Approve → Publish pattern preserves Meridian's existing governance structure exactly. The improvement is that the validation rules now run before the human reviewer sees the request, which means human time is spent on judgment calls rather than catching typos.

### Differences from Primous

- **Validation runs at request time, not at commit.** Primous validations were largely commit-time hooks. EDM Cloud validates as the author types, which catches issues before they hit the queue.
- **Single underlying node store with viewpoints.** Primous treated alternate hierarchies as parallel structures that had to be kept in sync manually. EDM Cloud's viewpoint model means the node is canonical and the view assignment is metadata.
- **REST API native integration with FCCS and PBCS.** Primous used scheduled exports. EDM Cloud uses live REST sync with diff-based delta packages, which means hierarchy changes flow into FCCS within minutes of commit rather than overnight.
- **Audit log is built in, not bolt-on.** Every request is auditable end-to-end without a separate audit framework.

## 2. Migration Approach

### Data extraction strategy

Source: Primous repository. Extract via Primous's native export utility into a structured CSV per hierarchy + a properties JSON per node type. Two passes:

- **Full extract of current production** (the live version that feeds FCCS today). Used as the seed for EDM Cloud.
- **Selective extract of historical snapshots** per the versioning strategy in Section 4.

Extracts run in week 1 and re-run in week 8 (incremental delta against any in-flight Primous changes during the migration window).

### Transformation and mapping

Two-stage transform:
1. **Schema mapping.** Primous columns to EDM Cloud properties, per the property list in Section 1. This is mechanical, scripted in Python, version-controlled in a migration repo.
2. **Validation pre-pass.** Every extracted node is run through the EDM Cloud validation rules before load. Nodes that fail validation are flagged into a reconciliation worklist for the data governance team to review with Corporate Accounting and Treasury.

The validation pre-pass is non-negotiable. Primous's looser validation regime means there are almost certainly nodes in production that would not pass EDM Cloud's tighter rules. We need to surface those before cutover, not during.

### Data validation and reconciliation checkpoints

Three checkpoints across the 12-week window:

- **Checkpoint 1, end of Week 4.** Source-side completeness: full extract row count matches Primous's repository count, checksum on Account Type and Balance Type properties matches, all 320 entities and 4,200 accounts accounted for.
- **Checkpoint 2, end of Week 8.** Target-side correctness: post-load row count matches extract, validation pre-pass exceptions resolved, FCCS test sync produces consolidated trial balance that matches Primous-fed FCCS to the penny on a frozen-as-of-Week-7 dataset.
- **Checkpoint 3, end of Week 12.** Cutover readiness: dry-run consolidation for one closed period using EDM Cloud as the metadata source produces results identical to the Primous-fed run, governance team has approved the workflow, all stakeholders signed off.

### Phasing across the three migration stages

**Weeks 1 to 4: Analysis & Design.**
- Week 1: Discovery interviews with Corporate Accounting, Treasury, Financial Planning, and Data Governance. Document current Primous configuration including all custom rules, reports, and integration points. Stand up Oracle EDM Cloud tenancy.
- Week 2: Configuration design document drafted (this document, peer-reviewed with Meridian's EPM team).
- Week 3: Validation rule design and FCCS mapping spec. Joint working sessions with FCCS owners.
- Week 4: Design sign-off. Reconciliation Checkpoint 1.

**Weeks 5 to 8: Migration Execution.**
- Week 5: EDM Cloud applications, node types, and viewpoints configured per the design.
- Week 6: Initial load of Entity hierarchy. Load validation. FCCS test sync of Entity-only metadata.
- Week 7: Initial load of Chart of Accounts. Load validation. FCCS test sync of full metadata. PBCS view test.
- Week 8: Validation pre-pass exceptions resolved with Corporate Accounting and Treasury. Reconciliation Checkpoint 2.

**Weeks 9 to 12: Testing & Stabilization.**
- Week 9: User Acceptance Testing scripts executed by Corporate Accounting (5 typical CoA changes), Treasury (5 typical entity changes), and Financial Planning (3 view consumption tests).
- Week 10: Parallel run. One full month-end close cycle with EDM Cloud as metadata source, Primous still maintained read-only. Outputs compared to the same period's actuals.
- Week 11: Governance workflow dry-run. End-to-end change request through Cloud workflows, full audit trail captured. Training sessions for each business team.
- Week 12: Final readiness review. Reconciliation Checkpoint 3. Go-live decision gate. Cutover Saturday of Week 12.

## 3. FCCS Integration Continuity

### Cutover approach: phased, with parallel validation

**Recommendation: Phased cutover by hierarchy, with a 1-week parallel validation period.** Not big bang, not full parallel run.

Rationale:
- **Big bang is too risky** in a fiscal year-end window. If something breaks at cutover, the fiscal close at Week 14 is exposed.
- **Full parallel run for the entire 12 weeks is too expensive** in operational overhead. Two governance workflows running side by side for 12 weeks is a recipe for drift between Primous and EDM Cloud.
- **Phased by hierarchy** lets us cut the simpler Entity hierarchy over first, prove FCCS is happy with EDM Cloud as the source, and then cut over the more complex Chart of Accounts the following week with confidence.

Sequence:
- **Week 11 Saturday: Entity cutover.** EDM Cloud becomes the source of truth for Entity. FCCS resyncs from EDM Cloud. Primous Entity goes read-only. 4-day soak period.
- **Week 12 Saturday: Chart of Accounts cutover.** EDM Cloud becomes the source of truth for CoA. FCCS resyncs. Primous CoA goes read-only.
- **Week 13 (one week before fiscal close opens): Soak period.** Both hierarchies live in EDM Cloud, FCCS consuming from EDM Cloud, no metadata changes allowed except emergency. Validate close-cycle metadata is correct.

### In-flight hierarchy changes during the migration window

Two rules:
1. **Change freeze for non-critical changes from Week 9 onward.** Anything that can wait until post-cutover, waits.
2. **Critical changes (regulatory, compliance, or close-cycle blocker) are dual-tracked.** The change is made in Primous via the existing process AND mirrored in EDM Cloud's pre-production environment by the consultant team. At cutover, EDM Cloud is already in sync.

This freeze is communicated to all three business teams in Week 5 with the cutover schedule, so they have lead time to push critical changes through before the freeze.

### Post-migration reconciliation

Three checks within 72 hours of each cutover:

- **Metadata count and checksum.** All nodes accounted for, all property values match the pre-cutover extract from Primous (frozen at cutover moment).
- **FCCS member mapping integrity.** Every account in EDM Cloud successfully maps to an FCCS member. Any unmapped accounts are flagged immediately to the FCCS owner and the consultant team.
- **Trial balance reproduction.** Run a closed prior-period consolidation in FCCS using EDM Cloud as the metadata source. Output must match the same period's audited Primous-fed actuals to the penny. Any variance triggers root cause analysis before the next close cycle.

A fourth check at 30 days post-cutover: validate that one full month-end close cycle with EDM Cloud as the metadata source produced clean results, no manual hierarchy fixes required.

## 4. Versioning & Archival Strategy

### What migrates to EDM Cloud

- The current production version of both hierarchies (the live version that feeds FCCS today)
- The last 4 quarter-end snapshots, covering the full prior fiscal year of close cycles

These are loaded as time-stamped versions in EDM Cloud, so the most-recent close cycle and three prior quarters can be reproduced from EDM Cloud directly, including any restatement work that touches the trailing twelve months.

### What gets archived

The remaining 86+ quarterly snapshots, spanning 5+ prior years.

Archival format: full extract per snapshot in CSV + JSON, written to immutable cold-storage (AWS S3 Glacier with object lock for write-once-read-many semantics, or Oracle Object Storage with retention rules, depending on Meridian's existing archival vendor). Each snapshot is a self-contained extract that includes node values, property values, hierarchy structure, and a manifest noting the Primous version stamp and the date of the closing period it represents.

### Rationale

**Business continuity.** Meridian needs the last fiscal year of close cycles immediately accessible. Restatements, audit responses, and management inquiries within the trailing twelve months all touch recent quarters. Anything older than that is rare-access data that can tolerate a slower retrieval path.

**Regulatory audit requirements applicable to a financial services firm.**
- **SOX Section 404** requires Meridian to retain documentation supporting internal controls over financial reporting. Practical interpretation in financial services: 7 years.
- **SEC Rule 17a-4** (broker-dealer recordkeeping, applicable to Meridian's wealth management arm) requires 6 years for most records, with the first 2 in immediately accessible storage.
- **State insurance commissioners** (relevant to Meridian's insurance arm) typically require 7 years and sometimes longer for specific record types.
- **GLBA + Reg S-P** (privacy and recordkeeping for financial institutions) imposes additional retention obligations.

The archival design honors the longest applicable retention (treat 7 years as the floor, retain longer where state insurance regs require) and keeps everything older than the trailing four quarters in compliant cold storage with documented retrieval procedures.

**Audit retrieval procedure.** Documented runbook stored alongside the archive: how to retrieve a snapshot, how to re-load it into a sandbox EDM Cloud environment for forensic inspection, expected SLA (24 hours from request to read-only sandbox).

The archive does not migrate to EDM Cloud as live versions because EDM Cloud is not an audit storage system, and paying SaaS license cost to host 6 years of cold data is wasteful. Cold storage with documented retrieval is the right architectural fit for the regulatory requirement.
