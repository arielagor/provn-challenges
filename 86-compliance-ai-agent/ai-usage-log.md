# PROVN Challenge 86: Compliance Document Intelligence Agent

## Section A. Design Rationale and Trade-offs

### Why this design

Three distinct agents with typed handoffs, not a single free-form loop. A Planner produces a structured Plan (tool sequence plus escalation triggers). An Executor consumes the Plan, calls the tools in order, and emits a structured ExtractionResult (claims with source spans, classification, routing proposal). A Verifier consumes the ExtractionResult, re-reads the broader window of the source document around every cited span, and either approves, requests a re-run of one Executor step, or escalates to human. Each agent has its own system prompt, its own tool subset, and its own memory. The handoffs between them are JSON-schema-typed, and every inter-agent handoff is recorded in the audit log alongside every tool call. The compliance workload is not a creative task. It is the same three steps on every document: extract, classify, propose. A free-form ReAct agent can invent a different plan each time, and the audit story for "why did the agent do it that way on document X" becomes impossible. Fixed plans with typed handoffs are boring and legible. Regulators like legible.

Tools as strict JSON schemas with explicit empty-string defaults instead of optional nulls. LLMs are more consistent when the schema tells them exactly what to send. An earlier draft had `deadline_iso` as an optional nullable field, and the model cheerfully sent `"deadline_iso": "TBD"` as a string value in the "optional" slot. Strings with an explicit "empty means no deadline" rule are cleaner.

Source spans on every extracted entity. This turns the agent output from "trust the model" into "check the quote." A human reviewer can see the exact sentence the model pulled the deadline from. Without this, the agent is faster than a junior analyst but no more trustworthy. With it, the reviewer becomes faster.

Routing to a team or a role, never to a named person. Named people go on vacation, change jobs, or leave the firm. Teams do not. The routing table is a YAML file a human owns. The agent reads it; the agent never writes it.

### Alternatives considered and rejected

**LangChain + a vector store of the full document corpus, with RAG.** Rejected. The failure mode is not "the model needs more context." The model has 200K context. The failure mode is that the document itself is the context, and paragraph 14 of 40 is exactly what the agent must not miss. Chunking with overlap and a verify-attribution step handles this better than RAG over the same document.

**Six agents, one per entity type, each with its own LLM and vector store.** Rejected. That flavor of multi-agent adds latency, adds per-agent state divergence, and the audit trail has to join across all of them. The Planner / Executor / Verifier split in the current design is the minimum agent count that buys enforceable role separation and the verify-attribution hard gate, without paying for six LLM pools. Three agents with typed handoffs are auditable top to bottom because each handoff is one row in the audit store.

**Fine-tuning a smaller model on the firm's historical routing decisions.** Rejected for phase one. The firm's historical decisions are the training data for the taxonomy and routing table, but baking them into a model means every taxonomy change requires a retrain. The firm updates its taxonomy whenever regulators issue guidance, which is several times a year. Keep the taxonomy as editable config.

**Structured-output APIs instead of tool calls.** A real option. Both Anthropic and OpenAI offer guaranteed-JSON output modes. The reason we went with tool calls: tool calls give us a natural checkpoint for the audit log. Each call and response is one row in the audit store. Structured output gives us one blob. The tool interface also lets us swap in a real extraction service (something OCR-aware) behind `extract_entities` later without rewriting the agent loop.

### Single biggest risk

Taxonomy drift, as described in failure mode 2 of the Agent Design Artifact. The model has its own internal definition of "AML" from training. The firm's definition moves with every new regulatory update. The model will confidently return the wrong category and the rest of the pipeline will accept it.

Mitigation: the taxonomy goes in the prompt as explicit allowed values, a weekly drift check re-classifies a sampled batch with a fresh LLM call, and the routing table is keyed on current taxonomy values so a drifted classification cannot find an owner and must escalate. If all three fail, a human reviewer still sees the source text next to the proposed route and catches the mismatch.

### Evaluation methodology

A scored benchmark is part of Phase 1, not future work. Two senior compliance analysts independently label all 200 historical documents on domain, urgency, owner team, deadline, and routability, constrained to the same enums the agent emits. Cohen's kappa is computed per-domain with a 0.75 gate, and tie-breaks go to the Head of Compliance. Scoring is per-category precision and recall, and any domain that cannot clear 0.90 precision and 0.85 recall is put on abstain, which routes the document to a generic human-triage queue with the agent classification attached as advisory text only. A weekly drift check of 20 live documents, re-labeled the same way, alerts if any domain falls below threshold for two weeks running. Full protocol in Section 6 of the Agent Design Artifact.

### Deployment strategy

Four phases from go-live, not "demo then launch." Phase 1A (weeks 3-4): shadow mode where the agent runs on every document but output goes only to an internal review queue; gate to advance is 85 percent agreement with human routing per-domain. Phase 1B (week 5): 10 percent random canary through the agent-first workflow; gate is 90 percent reviewer acceptance and reduced triage time. Phase 1C (weeks 6-8): 50 percent canary with daily per-domain drift checks. Phase 2 (month 3+): 100 percent with the human-approval gate preserved, requiring Head of Compliance sign-off in writing. Rollback triggers are precision-below-threshold for two weeks, reviewer acceptance under 80 percent in any canary phase, or any single incident where the agent's proposal would have caused a regulatory reporting miss. Full protocol in Section 7 of the Agent Design Artifact.

### Cost, latency, and rate-limit budget

Concrete planning numbers, not "fast enough." Per-document inference cost lands at about $0.09 on a Sonnet-class model (25,000 input tokens plus 1,200 output tokens at 2026 Anthropic prices), which rolls up to about $288 a month at the spec'd 3,200-document monthly volume. End-to-end latency target is under 60 seconds per document with a P95 under 90 seconds. Outbound calls are capped at 40 RPM by a token-bucket rate limiter on the orchestrator, leaving headroom under the Sonnet-class production-tier ceiling for retries and the weekly drift-check sampling. Full breakdown in Section 8 of the Agent Design Artifact, including the assumptions behind every number.

### Working code example

The runnable `agent_loop_stub.py` is now inlined in Section 9 of the Agent Design Artifact so a grader can read the actual code without leaving the submission. It shows the `extract_entities` tool schema, the fixed three-step agent loop, the append-only audit log, and the human-in-the-loop gate that labels every artifact "PROPOSED, AWAITS HUMAN APPROVAL" before exit.

### What I would change with two more weeks

Build the reviewer UI with keyboard shortcuts (approve, reject, ask question) instead of buttons. The whole point is to make the reviewer fast. Mouse-driven UIs are not fast. I would also use the extra time to widen the gold set beyond 200 documents into the 400 to 500 range, which gives tighter per-domain confidence intervals on the rarer domains (sanctions, conduct) where the current sample gets thin once you split by category.

## Section B. Stakeholder Brief (Head of Compliance)

This is a proposal for a software tool that reviews regulatory documents before your team does. It is not a replacement for your team. It is a first-pass reader.

What it does. The tool reads a regulatory document (a policy update, an audit report, a regulator filing) and produces a draft summary. The summary lists what the document is about, what actions it seems to require, when those actions are due, and which team inside the firm should probably own them. It also flags anything it could not figure out confidently, so your analyst knows where to look first.

What it does not do. It does not make any final decisions. It does not assign work. It does not file anything with anyone. Every draft it produces is marked "awaits human approval" in plain language. Your analyst still reviews every document before anything moves.

Why it helps. Your junior analyst currently spends 12 to 15 hours a week on first-pass triage. If the tool does the first pass, the same analyst spends roughly two to four hours a week reviewing drafts, and the rest of that time goes to harder work. The drafts come with the source sentences highlighted, so review is faster than writing from scratch.

A few terms. When this document says "LLM," it means a large language model, which is a kind of software that reads and writes text in plain English. When it says "audit trail," it means a complete record of what the tool read, what it decided, and why, that a regulator could request and we could produce.

What we are asking you to approve. Four weeks, two engineers, to build a prototype that reads a sample of 50 recent documents from our archive and produces drafts for your team to check. At the end of four weeks you decide whether it is accurate enough to trial on live work, or whether we stop.

What the next phase looks like if you say yes. Three months, one engineer, to wire the prototype into the existing document-intake queue, add the reviewer interface, and track accuracy on real live documents with your team's feedback.

Open questions before we commit to production. How fast do you need a first-pass draft ready after a document arrives? Who owns the routing table (the rule that says "AML questions go to this team")? What does the document retention policy require us to keep for the audit trail, and for how long?

## Section C. AI Usage Log

I used Claude, the LLM, to draft and iterate on this entire submission. The work below describes what I did with it, where I caught it producing wrong or lazy output, and what I designed without its help.

### What I used it for

**First draft of the tool schemas.** Claude produced three tools in one pass. The first draft had `deadline_iso` as a nullable optional field with `"type": ["string", "null"]` and `required: []`. I tested that shape against a mental model of how a Sonnet-class model would behave and caught the problem: nullable optionals let the model invent its own not-applicable marker. I changed the schema so `deadline_iso` is a required string and "empty string means no deadline." That is not a theoretical fix. It is a lesson from watching LLMs send `"TBD"` and `"N/A"` as string values into "optional" slots in prior work.

**First draft of the architecture.** Claude's first architecture proposal was, roughly, "three agents orchestrated by LangGraph, each with its own vector store, communicating via shared state." That is the generic tutorial structure. I pushed back hard: the failure mode on this job is not "the agent does not know enough," it is "the document itself is unstructured and the important sentence is buried." A multi-agent system does nothing for that. I redirected to a single supervisor loop with a fixed three-step plan, strict JSON tools, and a verify-attribution pass on deadlines. Claude then produced the design in the Agent Design Artifact, which is what you see now.

**First draft of the stakeholder brief.** The initial draft was full of "leverage," "robust pipeline," and "surface insights." A Head of Compliance does not read that and know what the thing does. I rewrote every sentence into plain English and added the two-sentence definitions of "LLM" and "audit trail." Every technical term that survives the rewrite has a plain-language gloss next to it.

**First draft of the failure modes.** Claude's first two failure modes were "hallucination" and "prompt injection." Hallucination is not a failure mode, it is a category. Prompt injection is a real risk but not specific to document intelligence. I threw out both and wrote the buried-detail-misextraction and taxonomy-drift modes independently, because those are the two things that actually break a compliance document pipeline in production. The buried-detail mode comes from thinking concretely about "paragraph 14 of a 40-page PDF." The taxonomy drift mode comes from knowing that regulators update their categories faster than models get retrained, and the model's training-time sense of "AML" will not match the firm's sense of "AML" six months later.

**Grader feedback pass on evaluation and rollout.** The first-round grader flagged two weak spots: the evaluation strategy was mentioned but not specified as a structured methodology, and the production rollout jumped from demo to three-month next phase without a shadow-or-canary plan. I pushed back with the kappa-gated gold set and the four-phase shadow-to-100-percent rollout. Claude drafted the section outlines; I picked the specific thresholds (kappa 0.75, precision 0.90, recall 0.85, shadow agreement 85 percent, canary acceptance 90 percent, rollback at 80 percent) based on what I would actually defend to a regulator, not what Claude proposed first. The per-domain abstain rule and the "any single regulatory miss trips rollback regardless of aggregate numbers" clause are mine. Claude's first instinct was to micro-average the precision-recall numbers, which would have let a strong DataPrivacy score paper over a bad Sanctions score. Per-category is not optional in a compliance context.

**Second grader-feedback pass on cost numbers and missing code.** The second round flagged two more gaps: cost and latency were hand-waved at "fast enough for batch processing" without concrete numbers, and the `agent_loop_stub.py` file was referenced but not bundled into the submission so a grader could not see the working code. I worked the cost math myself from token-per-page and 2026 Sonnet-class pricing, landing at $0.09 per document and $288 per month at the spec'd volume. Claude drafted prose around the numbers but did not pick them. I set the latency targets (60 seconds per document, P95 90 seconds) against the downstream triage SLA, which is hours, so the agent's job is to feed the reviewer queue cleanly rather than to win a benchmark. The 40 RPM token-bucket cap and the five-minute-delay retry policy with three-retry exhaustion are mine. The `agent_loop_stub.py` source is now inlined verbatim in Section 9 of the Agent Design Artifact, copy-pasted from the file on disk so the inlined version stays byte-identical to the runnable file.

**Third grader-feedback pass on architecture shape and the stub's verify-attribution gap.** The third round flagged two more gaps: the single supervisor loop with three sub-roles was structurally simpler than the "multi-agent system with explicit role separation" the top tier describes, and the stub demonstrated audit-log + HITL + fixed orchestration in code but kept `verify_attribution` as prose rather than running code. I restructured the architecture to three distinct agent classes (PlannerAgent, ExecutorAgent, VerifierAgent), each with its own SYSTEM_PROMPT constant, its own memory, and its own place in the pipeline. I added typed dataclasses for the handoffs (Plan, ExtractionResult, VerificationResult, ClaimCheck) so the JSON-schema boundaries between agents are visible in code, not hinted at in prose. I wrote `verify_attribution()` as a real function that locates each cited chunk inside the full document, pulls a broader window (2000 chars before and after), checks for verbatim presence of the claim's value, and for deadline claims scans for re-attributing section headings (the Tier-1-vs-vendor failure mode from Section 5). A failed check raises a `VerificationFailure` that the orchestrator catches and translates into a re-run of just that Executor step, with a one-rerun budget; a second failure escalates to human. The audit log gained an `agent_role` field so inter-agent handoffs are first-class events, not hidden inside tool-call payloads. The three-agent shape is worth the added state complexity because it makes the verify-attribution pass an enforceable structural gate between Executor and Verifier rather than advisory prose the LLM might silently skip. Claude drafted the class skeletons and the mock-response plumbing; I picked the check semantics (verbatim-presence plus heading-contradiction for deadlines), the rerun-budget policy, and the decision that Verifier cannot approve its own routing decision (the HITL gate still runs downstream regardless).

### Component I designed independently

The failure mode analysis. Claude's default output for that section was generic and would not have caught the real bugs. I wrote both failure modes end to end: the mechanism, how we catch it, how we mitigate if we do not catch it.

### Component Claude drafted and I lightly edited

The tool schema JSON syntax and the agent-loop skeleton in `agent_loop_stub.py`. Claude is good at boilerplate. I kept the structure and edited the details (field types, stop conditions, the human-in-the-loop label). That split is on purpose. Use Claude for structure and boilerplate. Do the thinking yourself where the answer matters.
