# Agent Design Artifact: Compliance Document Intelligence Agent

## 1. Agent Architecture

### Three Distinct Agents With Typed Handoffs

The architecture is a multi-agent system, not a single supervisor loop. Three agents, each with its own system prompt, its own tool subset, and its own memory. The handoffs between them are typed JSON schemas, not free-form text. The audit log records every inter-agent handoff alongside every tool call, which strengthens the regulatory trail.

**Planner agent.** Receives a new document. Produces a structured Plan: which tools to call, in what order, what artifacts to expect, and what conditions should trigger escalation instead of a routing proposal. The Plan is a typed object (step list, expected artifacts, escalation triggers). The Planner does not call tools. Its memory is a plan log keyed by document id.

**Executor agent.** Consumes the Plan, calls tools in order, produces a structured ExtractionResult: claims (risk areas, required actions, responsible-party hints, deadlines, cited regulations, each with a chunk id and a source span), a classification (domain plus urgency), and a routing proposal. Its memory is an extraction scratchpad that the Verifier never sees directly; only the final ExtractionResult crosses the handoff boundary.

**Verifier agent.** Consumes the ExtractionResult, runs a focused verification pass on every claim, and either approves, requests a re-run of one Executor step, or escalates to a human. Verification includes a verify-attribution pass that re-reads a broader window of the source document around each cited span, a cross-check for conflicting deadlines, a domain-enum validity check against the routing table, and a routing-miss guard. The Verifier cannot approve its own routing decision. The HITL gate still runs downstream. Its memory is the per-document list of ClaimCheck results.

### Typed Handoff Schemas

Three JSON schemas govern the inter-agent boundaries:

- `Plan`: `{document_id, steps: [{step_id, tool, reason}], expected_artifacts, escalation_triggers}`.
- `ExtractionResult`: `{document_id, claims: [{claim_id, claim_type, value, chunk_id, source_span, deadline_iso, confidence}], classification, proposal}`.
- `VerificationResult`: `{document_id, checks: [{claim_id, passed, reason, broader_context_excerpt}], approved, rerun_step_id, escalate_to_human, escalation_reason}`.

A failed attribution check raises a `VerificationFailure` that carries the step_id the Executor should re-run. The orchestrator catches it, re-runs only that step with a correction hint, and resubmits to the Verifier. A second failure on the same step escalates to human.

### Why three agents and not one

The added state complexity buys two things that matter on regulatory work. First, specialization lets each agent's system prompt be tight and independently testable. The Planner prompt never mentions routing tables; the Executor prompt never mentions escalation criteria; the Verifier prompt never mentions tool schemas. Each prompt is shorter than a unified one would be, easier to version, and easier to swap when the taxonomy changes. Second, the verify-attribution defense becomes an enforceable hard gate between Executor and Verifier rather than an advisory line of prose. A failing attribution cannot slip through because the routing proposal is never visible to the HITL reviewer until the Verifier has signed off. In a single-loop design, verify-attribution is a step the LLM is supposed to run but may silently skip under load or prompt drift. Splitting it out makes skipping structurally impossible.

### Role responsibilities in one line each

**Planner.** Pick the tool sequence. List the escalation triggers. Do not execute.

**Executor.** Call tools in the Plan's order. Return claims with source spans, a classification, and a routing proposal. Do not self-verify.

**Router (inside Executor).** Propose an owner (a team or a named role, not a person) and a due date. The proposal carries a confidence score and a list of open questions. The router never authorises an action; the Verifier and the HITL gate do that.

### Memory Strategy

Three kinds of memory. Keep them separate so the audit trail stays clean.

1. **Per-document working memory.** Everything the agent extracted from the current document, plus every tool call and every tool response. Flushed to the audit log at the end of each run. Not reused across documents.
2. **Long-term taxonomy memory.** The firm's own list of compliance domains, the firm's routing table (domain plus risk area maps to owner), and a glossary of internal terms. Stored as a versioned YAML file in S3 or Blob, loaded into the prompt at run time, never mutated by the agent. A human edits it.
3. **Retrieval memory.** Chunks of prior regulatory documents and prior routing decisions, indexed in OpenSearch or Azure AI Search. The agent can cite a prior similar document when proposing a route, which gives the reviewer something to compare against.

No fine-tuning. No vector store that learns from user feedback automatically. Learning goes through human review and manual taxonomy edits.

### LLM Selection

Claude Sonnet as the default. Reasoning: this is a long-context, document-heavy workload where the cost of a missed deadline buried on page 27 is much higher than the cost of a few extra tokens. Sonnet handles 200K context, follows JSON schemas reliably, and is strong at quoting source text verbatim, which matters for the audit trail.

Fallback option: GPT-4 class model behind the same tool interface, so the firm is not locked to one vendor. The orchestration code treats the LLM as a pluggable component. No LangChain. The abstraction is a thin `LLMClient` class with `complete(messages, tools)` and nothing else.

Not using a small model. Savings do not justify the risk on regulatory text, and this workload is measured in hundreds of documents a week, not millions.

### Flow Control: Stop, Retry, Escalate

The orchestrator runs at most eight tool calls per document across all three agents. After that it stops and escalates, no matter what. The Executor is allowed exactly one re-run per Verifier-requested step before the orchestrator escalates.

It stops (success) when the Verifier approves and all of the following are true: at least one risk area extracted, at least one action extracted, a domain assigned with confidence at or above 0.7, a deadline extracted or an explicit "no deadline cited" finding, and a proposed owner drawn from the routing table.

It retries a tool call once on transient errors (timeout, 5xx, JSON parse failure). On the second failure it surfaces the error to the reviewer and continues without that tool's output, flagging the gap in the summary.

It escalates to a human (without proposing a route) when: domain confidence is below 0.7, the document cites a regulator the taxonomy does not recognize, two extracted deadlines conflict, the Verifier requests a re-run and the re-run fails too, or the router cannot find an owner in the routing table for the extracted domain plus risk-area pair.

## 2. Tool Definitions

Three tools. All strict JSON schema. All descriptions written to reduce ambiguity, not to sound natural.

### Tool 1: `extract_entities`

```json
{
  "name": "extract_entities",
  "description": "Extract compliance entities from a single chunk of document text. Returns structured entities with character-offset spans into the chunk so each entity can be traced back to source text. Do not summarize. Do not paraphrase deadlines into relative dates; return the exact date string as it appears, plus a normalized ISO date if unambiguous.",
  "input_schema": {
    "type": "object",
    "properties": {
      "chunk_text": {
        "type": "string",
        "description": "Raw text of the chunk. Up to 8000 characters."
      },
      "chunk_id": {
        "type": "string",
        "description": "Stable identifier for the chunk, e.g. doc123_chunk_07. Used for audit logging."
      },
      "document_type_hint": {
        "type": "string",
        "enum": ["policy_update", "audit_report", "regulatory_filing", "enforcement_action", "unknown"],
        "description": "Optional hint from an earlier classification pass. Pass 'unknown' if not yet classified."
      }
    },
    "required": ["chunk_text", "chunk_id"]
  }
}
```

Returns a list of entities, each with `type` (risk_area, required_action, responsible_party_hint, deadline, cited_regulation), `value`, `source_span` (start and end offsets), and `confidence`. The `source_span` field is the audit-trail anchor. Any downstream claim the agent makes must be traceable to a span.

### Tool 2: `classify_document`

```json
{
  "name": "classify_document",
  "description": "Classify a document by compliance domain and urgency, using the firm's current taxonomy. Returns the top domain with a confidence score, plus up to two alternate domains if the top is below 0.9. Urgency is a discrete enum, not a numeric score. If the document cannot be confidently placed in the taxonomy, return domain='unrecognized' and confidence reflecting that.",
  "input_schema": {
    "type": "object",
    "properties": {
      "extracted_entities": {
        "type": "array",
        "description": "Entities previously returned by extract_entities, flattened across all chunks.",
        "items": { "type": "object" }
      },
      "document_summary": {
        "type": "string",
        "description": "One-paragraph summary the agent has drafted from the extracted entities. Used to disambiguate between close domains (e.g. AML vs sanctions)."
      },
      "taxonomy_version": {
        "type": "string",
        "description": "Version identifier of the firm's taxonomy in use, e.g. '2026-03-taxonomy-v4'. Required so a future reviewer can reproduce the classification against the same taxonomy."
      }
    },
    "required": ["extracted_entities", "document_summary", "taxonomy_version"]
  }
}
```

### Tool 3: `propose_routing`

```json
{
  "name": "propose_routing",
  "description": "Propose a routing decision given an extracted set of entities and a classification. Returns a proposed_owner (team or role, never an individual by name), a proposed_due_date, a confidence score, and a list of open_questions the human reviewer must answer before this can be approved. If confidence is below 0.7 or if open_questions is non-empty, the caller MUST mark the proposal as 'awaits_human_review' and MUST NOT treat it as final.",
  "input_schema": {
    "type": "object",
    "properties": {
      "domain": {
        "type": "string",
        "description": "The compliance domain returned by classify_document."
      },
      "urgency": {
        "type": "string",
        "enum": ["immediate", "this_quarter", "monitoring"],
        "description": "Urgency bucket from classify_document."
      },
      "risk_areas": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Risk areas extracted from the document."
      },
      "deadline_iso": {
        "type": "string",
        "description": "Normalized ISO date of the earliest hard deadline, or empty string if none."
      },
      "routing_table_version": {
        "type": "string",
        "description": "Version of the routing table YAML the agent is consulting."
      }
    },
    "required": ["domain", "urgency", "risk_areas", "routing_table_version"]
  }
}
```

Note that `deadline_iso` is a string (possibly empty), not a null and not an optional. LLMs are more consistent with explicit empty strings than with optional-null fields, and this avoided a bug in an earlier draft where the model cheerfully sent back `"deadline_iso": "TBD"` as a string value for an optional field.

## 3. Orchestration Logic

Three agents run in sequence, each producing a typed artifact the next consumes. Not ReAct-style free-form reasoning, because free-form reasoning is where audit trails go to die.

```
1. Ingest document from S3 or Blob URI.
2. Split into chunks (8000 chars, 500 char overlap, chunk at paragraph boundaries when possible).
3. Planner.run(document_id, chunks) -> Plan
4. Executor.run(Plan, chunks) -> ExtractionResult
     (Executor calls extract_entities per chunk, then classify_document, then propose_routing, in that order)
5. Verifier.run(ExtractionResult, document_text, chunks) -> VerificationResult
     (Verifier runs verify_attribution on every claim, conflict checks, and routing-miss guard)
6. If Verifier raises VerificationFailure with step_id=X:
     Executor.run(Plan, chunks, correction_hint="re-read for X") -> ExtractionResult'
     Verifier.run(ExtractionResult') -> VerificationResult
     (budget: exactly one rerun; second failure escalates to human)
7. If Verifier escalates (conflict, routing miss, rerun budget exhausted):
     emit ESCALATED artifact; no proposal.
8. Otherwise emit final artifact labeled "PROPOSED, AWAITS HUMAN APPROVAL".
9. Audit log captures every agent handoff with agent_role tags, plus every tool call.
```

Tool-selection order inside the Executor is fixed: extract, classify, propose. The Planner does not get to pick a different order. This is on purpose. A free-form agent can decide to classify before extracting, which then anchors extraction to a wrong-guessed domain and produces confident-looking nonsense.

Stop conditions: the success conditions listed in Flow Control, the eight-tool-call ceiling, the one-rerun budget, or any escalation trigger. Every stop writes a final artifact. There is no silent exit.

## 4. Working Code Example

See `agent_loop_stub.py` in this folder, also inlined verbatim in Section 9 below. That file contains: the `extract_entities` tool schema, three agent classes (PlannerAgent, ExecutorAgent, VerifierAgent) with their own system prompts and memory, typed handoff dataclasses (Plan, ExtractionResult, VerificationResult), a `verify_attribution()` function that re-reads every claim against a broader window of the source document, an audit log that records every inter-agent handoff with an `agent_role` tag, a one-rerun budget for Verifier-requested re-extractions, and a human-in-the-loop gate that labels the final output "PROPOSED, AWAITS HUMAN APPROVAL" before exit. It runs without external dependencies and prints a full trace.

## 5. Failure Mode Analysis

Two failure modes specific to document intelligence on regulatory text. Not generic. Each with a catch and a mitigation.

### Failure Mode 1: Buried-Detail Misextraction

The problem. A 40-page audit report mentions, in paragraph 14, that a specific vendor-oversight deadline falls on the 15th of the month following the next quarterly board meeting. Everything else in the document is about capital adequacy. The agent chunks the document. The relevant paragraph lands in a chunk whose surrounding text is about Tier 1 ratios. The LLM, primed by the chunk's context, reads the deadline as a capital-reporting deadline, extracts it, and the router sends the whole item to the Capital team with a date a month too early. Capital team dismisses it as a false positive. The real owner, Vendor Risk, never sees it.

This is not hallucination. The model extracted a real sentence from the real document. It got the attribution wrong because the chunk boundary stripped the attribution context.

How we catch it. Two defenses, stacked.

First, every extracted entity carries a `source_span` that points back to the exact characters in the chunk. The summary step is required to cite at least one source_span per claim. If a claim has no span, it is dropped before classification. This will not catch a wrong attribution, but it will catch hallucinated attributions.

Second, chunking is done with 500-character overlap at paragraph boundaries, and every extracted deadline is re-checked against a broader window (the chunk plus 2000 characters before and after) in a separate "verify_attribution" LLM call before it can become a hard deadline. If the verify call disagrees with the initial attribution, the deadline is tagged ambiguous and surfaced as an open_question for the reviewer. In practice this catches the Tier-1-vs-vendor case because the broader window contains the heading "Third-Party and Vendor Oversight" two paragraphs earlier.

Mitigation if it still gets through: the routing proposal always cites source text. A human reviewer sees the cited sentence, the cited section heading, and the proposed owner side by side. They can catch the mismatch in seconds. The agent's job is to make the reviewer fast, not to be right without supervision.

### Failure Mode 2: Taxonomy Drift Between Training and the Firm's Internal Usage

The problem. The LLM was trained on a world where "AML" means anti-money-laundering broadly. The firm's internal taxonomy, as of the last regulatory update, has split AML into three sub-categories: transaction monitoring, customer due diligence, and correspondent banking. A new document arrives that is clearly a correspondent banking guidance update. The LLM classifies it as "AML" with confidence 0.95 because that is the label its training data taught it. The firm's routing table has no entry for bare "AML" anymore. The router either picks the wrong sub-category (drifts to transaction monitoring because that is alphabetically first in the YAML) or returns an error and escalates everything AML-related until someone notices.

This is the more dangerous failure because it looks like success. The agent is confident. The extraction is right. The classification is wrong in a way that the LLM has no way to self-detect, because its internal definition of "AML" is right, and the firm's definition has moved.

How we catch it. Two defenses.

First, the taxonomy is passed into `classify_document` as explicit text in the prompt, not assumed from training. The prompt says: "These are the only valid domain values. Do not return any value not in this list. If the document does not fit, return 'unrecognized'." The `taxonomy_version` field gets logged with every classification, so a future audit can ask "what was the taxonomy when this was classified?" and get an answer.

Second, a weekly drift check. A small batch of newly-classified documents is sampled and re-classified by a second LLM call with only the taxonomy and the document summary, with no memory of the first pass. If the two passes disagree on more than 5 percent of sampled documents, the drift alarm fires and a human reviews the taxonomy. This is how we detect the case where the LLM quietly defaults to a stale category name it learned in training.

Mitigation if it still gets through: the routing table is the last backstop. It is keyed on the current taxonomy's domain values. A drifted classification cannot find a row. The router returns `proposed_owner='unassigned'` with an open_question that names the unmatched domain. The reviewer sees it immediately.

## 6. Evaluation Methodology

The weekly drift check described in Failure Mode 2 is a live-traffic monitor, not a benchmark. A benchmark is what tells you the agent is fit to touch live traffic at all. This section specifies the benchmark.

### Gold Set Construction

Two hundred historical documents drawn from the last four quarters of the firm's own intake, sampled to match the domain distribution the agent will see in production. Not a convenience sample. If sanctions documents are 8 percent of real intake, they are 8 percent of the 200.

Each document is labeled independently by two senior compliance analysts on five fields: compliance_domain, urgency bucket, owner team, key deadline date as an ISO string, and a routability flag that indicates whether a human would route this document at all or would escalate it outright. The label schema is bound to the same enums the agent emits. Domain labels must be one of AML, DataPrivacy, CapitalRequirements, Sanctions, Conduct, or Unrecognized. Urgency must be immediate, this_quarter, or monitoring. Owner team must be a value in the current routing table YAML. This constraint matters. If labelers can pick from a different vocabulary than the agent, the benchmark is measuring the wrong thing.

Labelers do not see each other's labels until their own pass is complete. They see the document, the taxonomy YAML, and the routing table. They do not see model output on the same document, ever.

### Inter-Rater Reliability

Cohen's kappa is computed on domain and on urgency for the two labelers, per domain (so we can see whether sanctions is confusable with AML at the human level before we blame the model for it). Kappa threshold is 0.75. Documents with kappa disagreement on domain or urgency go to a third labeler, the Head of Compliance or a designee, whose call is final.

Disagreement patterns matter on their own. If two senior analysts cannot agree on whether a document is AML or Sanctions, that is a taxonomy-ambiguity signal and it gets logged to a separate review queue. The fix there is not a better model. The fix is a cleaner taxonomy, owned by Compliance, edited in YAML.

### The Benchmark Is Part of Phase 1

The gold set is not future work. It is week two of the four-week phase. Twenty hours of senior-analyst time budgeted for the labeling pass, plus a few hours of the Head of Compliance for tie-breaks. The agent does not ship to shadow mode (Phase 1A below) without a scored benchmark. No exceptions. An agent that has never been measured against a human-labeled set is not trustworthy, and "trust me, the demo looked good" is not a compliance posture.

### Scoring

Precision and recall per-category, not micro-averaged. Micro-average hides the case where the agent is 95 percent accurate overall because it nails DataPrivacy and is worthless on Sanctions. The firm cares about Sanctions performance on Sanctions documents.

Per-domain minimum thresholds before the agent is allowed to propose a routing decision for that domain:

- Precision at or above 0.90 on the gold set.
- Recall at or above 0.85.
- Deadline extraction exact-match at or above 0.95 on documents where a deadline exists.

A domain that fails to clear threshold is put on abstain. The agent sees a document in that domain, classifies it, and routes to a generic human-triage queue with the proposed classification attached as advisory text, not as a decision. The abstain list is visible to reviewers and reviewed weekly.

### Weekly Drift Check

Twenty live documents sampled per week after go-live, re-labeled by the same protocol (two analysts, kappa gate, tie-break). Agent output is compared to the fresh labels. Alert fires if precision or recall on any domain falls below threshold for two consecutive weeks. The alert goes to the Head of Compliance and the on-call engineer. The action when the alert fires is to roll that domain back to abstain until a retrain, taxonomy update, or bug fix clears it.

The drift check is separate from the gold-set benchmark. The gold set is the fixed reference. The weekly sample is the running probe. They answer different questions.

## 7. Deployment Strategy

Four phases from go-live. A single "demo and then launch" gate is not a deployment strategy, it is a wish. The phasing below assumes the Phase 1 gold-set benchmark has been cleared on every domain the agent is allowed to propose for.

### Phase 1A: Shadow Mode (Weeks 3-4, end of Phase 1)

Every incoming document in production is processed by the agent. The agent's output goes to an internal review queue only, not to the human reviewer workflow that actually routes the document. The document continues through the existing human-only path in parallel. Two senior compliance analysts inspect the agent's proposed decision alongside the human routing that actually happened.

The metric that matters here is agreement rate with human routing, broken down by domain. The gate to advance is 85 percent or higher agreement on every non-abstained domain. Domains that do not clear 85 percent stay on abstain.

Shadow mode catches a specific class of bug the gold-set benchmark cannot catch: documents the agent has never seen the shape of, because the firm's intake changes. The gold set is a fixed reference. Live traffic is a moving one.

### Phase 1B: 10 Percent Canary (Week 5, first post-launch week)

A random 10 percent of incoming documents are routed through the agent-first workflow. On that 10 percent, the human reviewer sees the agent's proposal and source-span citations, and approves, edits, or rejects. The other 90 percent continue on the existing human-only path.

The metrics are reviewer acceptance rate on the 10 percent path and triage SLA. The gate to advance is reviewer acceptance at or above 90 percent and triage time reduced versus the baseline path. Triage time going up is a failure even if acceptance is high, because the whole point is to make the reviewer faster.

### Phase 1C: 50 Percent Canary (Weeks 6-8)

If 1B clears, scale to half of incoming traffic. The specific thing to watch during this phase is domain-specific regression. The taxonomy-drift failure mode from Section 5 is most likely to surface here, because a 50 percent sample is large enough to see per-domain problems that a 10 percent sample masks with noise. Per-domain precision and recall on the live-sampled drift check gets a daily look during this phase, not weekly.

### Phase 2: 100 Percent With HITL Preserved (Month 3 and beyond)

Every incoming document goes through the agent-proposal path. Every proposal still requires human approval before it becomes a routing action. The human approval gate is non-negotiable per the HITL constraint in the spec and does not relax at any traffic percentage. The shift from 1C to Phase 2 requires Head of Compliance sign-off on the agreement-rate and reviewer-acceptance numbers from the prior phase, in writing, recorded in the audit store.

### Rollback Triggers

Any one of these trips a rollback to the previous phase:

1. Precision on any non-abstained domain drops below threshold for two consecutive weeks on the live drift check.
2. Reviewer acceptance drops below 80 percent in any canary phase for a full week.
3. Any single incident where the agent's proposal, if accepted, would have caused a regulatory reporting miss. This is a "one strike and you step back" rule regardless of the aggregate numbers.

Rollback is not a failure. It is how the system stays honest about its own uncertainty. A phase that advances and then rolls back has still produced useful information.

## 8. Cost, Latency, Token Budget, and Rate Limits

The agent ships into a workload of about 800 documents a week, roughly 3,200 a month. That is small enough that the inference bill is a rounding error against an analyst's loaded hour, but big enough that a careless prompt can blow the rate limit and stall the queue. The numbers below are the planning budget. They are estimates, not measurements, and they assume Anthropic Sonnet-class pricing as of 2026 (input around $3 per million tokens, output around $15 per million). Re-baseline once real traffic lands.

### Token Budget Per Document

A representative regulatory PDF runs about 40 pages, which lands at roughly 25,000 to 50,000 characters of extracted text. The chunking strategy from Section 3 cuts that into three or four 8,000-character chunks with overlap, so each chunk costs about 2,000 to 4,000 input tokens once the schema and instruction overhead is added. Across the agent's two iterations (the per-chunk extract pass plus a single classify-and-propose pass over the aggregated entities), total input lands at 16,000 to 30,000 tokens per document, with a working planning number of 25,000.

Output is much smaller. The structured JSON for entities, summary, classification, and routing proposal, plus the audit-log entries, runs 800 to 1,500 tokens. Working planning number is 1,200.

So the per-document budget is about **25,000 input tokens and 1,200 output tokens** on a Sonnet-class model.

### Per-Document Cost Projection

At Anthropic Sonnet-class 2026 pricing, the math is:

- Input: 25,000 tokens at $3 per million is about $0.075 per document.
- Output: 1,200 tokens at $15 per million is about $0.018 per document.
- Total: about **$0.09 per document** in inference cost.

Monthly volume is 800 documents per week times four weeks, or 3,200 documents. That is **about $288 per month** in inference cost. For comparison, a single hour of a senior compliance analyst costs the firm more than an entire month of agent inference. The cost case is not the bottleneck; the trust case is.

The Phase 1 gold-set labeling loop has a separate one-time cost. Two hundred documents, two labelers, re-run twice during the benchmark build to validate the inter-rater protocol, is roughly 800 inference passes at the same per-document rate. Call it **about $60 one-time** for the benchmark build, plus the analyst time, which is the actual expensive part.

### Latency Targets

End-to-end per document, from "PDF arrives in S3" to "final artifact written to the audit store," the target is **under 60 seconds**. The agent loop is bounded at three tool calls (extract, classify, propose), and each tool call is a single LLM round-trip on chunked input. P95 target is **under 90 seconds**, which gives headroom for the verify-attribution second-pass on flagged deadlines and for occasional retries on transient errors.

The downstream triage SLA is measured in hours, not seconds. The reviewer queue is the actual bottleneck. The agent's job is to feed that queue cleanly, not to win a latency benchmark.

Batch processing window: an overnight drain of one full business day's intake, roughly 160 documents, finishes in under three hours at the 60-second per-document target with a single worker. Two workers cover the weekly peak with idle headroom.

### Rate Limits

Anthropic Sonnet-class production-tier limits as of 2026 are roughly **50 requests per minute and 40,000 tokens per minute** for a typical paid account. At an average peak of 800 documents per week spread across business hours, the agent fires off roughly two documents per hour per worker, which is well below either ceiling.

A token-bucket rate limiter on the orchestrator caps outbound calls at **40 RPM** to leave headroom for retries and for the weekly drift-check sampling that runs alongside production traffic.

If the API does return a 429, the document is queued with a five-minute delay retry, capped at three retries. On exhaustion, the orchestrator escalates to on-call with a structured alert that names the document ID and the upstream error code. This is the audit-trail-compatible degrade path. The document is not lost. It is parked, visible, and recoverable.

### Why These Numbers Are Defensible

Token-per-page comes from a back-of-envelope of 600 to 1,200 characters per page on a regulatory document, divided by an average of four characters per token. Pricing comes from Anthropic's published Sonnet-class rates as of 2026 and may shift; the dollar number above will move with it but the order of magnitude will not. Volume comes from the spec ("hundreds of documents a week"). Rate-limit headroom assumes a single-tenant production tier; if the firm runs multiple agents on the same API key, the orchestrator's RPM cap drops accordingly.

If real traffic comes in 3x heavier than spec or pricing tightens, the numbers move but the design does not. The cost case is robust at this volume. The latency case is the one to watch, because reviewer experience degrades quickly past two minutes per document.

## 9. Working Code Example (agent_loop_stub.py)

The runnable stub below demonstrates the multi-agent architecture in code: three distinct agent classes (Planner, Executor, Verifier) with their own system prompts, their own memory, and typed handoffs (Plan, ExtractionResult, VerificationResult). It shows `verify_attribution()` as real code, not prose: the Verifier re-reads a broader window around every claim's cited span and raises `VerificationFailure` when the broader context contradicts the claim, which triggers a re-run of just that Executor step. The audit log records every inter-agent handoff with an `agent_role` tag. External services and LLM calls are mocked so the file runs as-is with `python agent_loop_stub.py` and prints a full trace plus the final JSON artifact.

```python
"""
PROVN Challenge 86: Compliance Document Intelligence Agent (runnable stub, v4)

This stub demonstrates the multi-agent architecture described in agent-design.md.
Three distinct agent classes, each with its own system prompt, its own tool
subset, and its own memory. Typed handoffs between them. Verify-attribution
runs as real code, not as prose.

Demonstrated here:
  * PlannerAgent, ExecutorAgent, VerifierAgent classes, each with a
    SYSTEM_PROMPT docstring constant and a run() method.
  * Typed dataclasses for the handoffs: Plan, ExtractionResult, VerificationResult.
  * verify_attribution() re-reads each claim against a broader window of the
    source document. If the broader window contradicts the claim, the Verifier
    raises VerificationFailure and the main loop re-runs just that step.
  * Audit log with an agent_role field so inter-agent handoffs are traceable,
    not just tool calls.
  * HITL gate: the final artifact is labeled PROPOSED, AWAITS HUMAN APPROVAL.

LLM calls are mocked (_mock_llm_call). verify_attribution() is real code.
Run with:
    python agent_loop_stub.py

No external dependencies.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


# ----------------------------------------------------------------------------
# Tool schema (one of three defined in agent-design.md; inlined for reference)
# ----------------------------------------------------------------------------

EXTRACT_ENTITIES_SCHEMA: dict[str, Any] = {
    "name": "extract_entities",
    "description": (
        "Extract compliance entities from a chunk. Each entity carries a "
        "source_span (char offsets) so it can be traced back to the chunk."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "chunk_text": {"type": "string"},
            "chunk_id": {"type": "string"},
            "document_type_hint": {
                "type": "string",
                "enum": ["policy_update", "audit_report", "regulatory_filing",
                         "enforcement_action", "unknown"],
            },
        },
        "required": ["chunk_text", "chunk_id"],
    },
}


# ----------------------------------------------------------------------------
# Typed handoff schemas (dataclasses stand in for JSON schemas between agents)
# ----------------------------------------------------------------------------

@dataclass
class PlanStep:
    step_id: str
    tool: str
    reason: str


@dataclass
class Plan:
    document_id: str
    steps: list[PlanStep]
    expected_artifacts: list[str]
    escalation_triggers: list[str]


@dataclass
class ExtractedClaim:
    claim_id: str
    claim_type: str
    value: str
    chunk_id: str
    source_span: dict[str, int]
    deadline_iso: str
    confidence: float


@dataclass
class ExtractionResult:
    document_id: str
    claims: list[ExtractedClaim]
    classification: dict[str, Any]
    proposal: Optional[dict[str, Any]]


@dataclass
class ClaimCheck:
    claim_id: str
    passed: bool
    reason: str
    broader_context_excerpt: str


@dataclass
class VerificationResult:
    document_id: str
    checks: list[ClaimCheck]
    approved: bool
    rerun_step_id: Optional[str]
    escalate_to_human: bool
    escalation_reason: Optional[str]


class VerificationFailure(Exception):
    """Raised by Verifier when a claim fails attribution. Carries the step_id
    the Executor should re-run."""

    def __init__(self, step_id: str, checks: list[ClaimCheck]):
        super().__init__(f"Verification failed; rerun step {step_id}")
        self.step_id = step_id
        self.checks = checks


# ----------------------------------------------------------------------------
# Audit log (append-only, records inter-agent handoffs, not just tool calls)
# ----------------------------------------------------------------------------

@dataclass
class AuditEvent:
    ts: str
    agent_role: str
    event_type: str
    payload: dict[str, Any]


@dataclass
class AuditLog:
    document_id: str
    events: list[AuditEvent] = field(default_factory=list)

    def record(self, agent_role: str, event_type: str, payload: dict[str, Any]) -> None:
        ev = AuditEvent(
            ts=datetime.now(timezone.utc).isoformat(),
            agent_role=agent_role,
            event_type=event_type,
            payload=payload,
        )
        self.events.append(ev)
        line = json.dumps(payload, default=str)
        if len(line) > 220:
            line = line[:220] + "..."
        print(f"[AUDIT {self.document_id}] {ev.ts} {agent_role}/{event_type}: {line}")


# ----------------------------------------------------------------------------
# Canned mock responses (per agent role, per call index)
# ----------------------------------------------------------------------------

_CANNED_RESPONSES: dict[str, list[dict[str, Any]]] = {
    "planner": [{
        "steps": [
            {"step_id": "s1_extract", "tool": "extract_entities", "reason": "pull entities per chunk"},
            {"step_id": "s2_classify", "tool": "classify_document", "reason": "assign domain and urgency"},
            {"step_id": "s3_propose", "tool": "propose_routing", "reason": "propose owner and due date"},
        ],
        "expected_artifacts": ["claims", "classification", "proposal"],
        "escalation_triggers": [
            "domain confidence below 0.70",
            "unrecognized regulator",
            "two deadlines conflict",
            "routing table miss on domain",
        ],
    }],
    "executor": [{
        "claims": [
            {"claim_id": "c_risk_01", "claim_type": "risk_area",
             "value": "correspondent banking onboarding",
             "source_span": {"start": 42, "end": 79},
             "deadline_iso": "", "confidence": 0.88},
            {"claim_id": "c_action_01", "claim_type": "required_action",
             "value": "update their customer due diligence policy to reflect the new jurisdiction",
             "source_span": {"start": 120, "end": 210},
             "deadline_iso": "", "confidence": 0.82},
            {"claim_id": "c_deadline_01", "claim_type": "deadline",
             "value": "15 July 2026",
             "source_span": {"start": 260, "end": 275},
             "deadline_iso": "2026-07-15", "confidence": 0.91},
            {"claim_id": "c_cited_01", "claim_type": "cited_regulation",
             "value": "FinCEN advisory 2026-07",
             "source_span": {"start": 15, "end": 40},
             "deadline_iso": "", "confidence": 0.95},
        ],
        "classification": {
            "domain": "aml_correspondent_banking",
            "domain_confidence": 0.86,
            "urgency": "this_quarter",
            "alternate_domains": ["aml_customer_due_diligence"],
            "taxonomy_version": "2026-03-taxonomy-v4",
        },
        "proposal": {
            "proposed_owner": "Financial Crimes Team",
            "proposed_due_date": "2026-07-15",
            "confidence": 0.79,
            "open_questions": [],
            "routing_table_version": "2026-04-routing-v2",
        },
    }],
    # Verifier uses real code (verify_attribution) rather than a canned LLM
    # response. The entry is kept so the role-to-LLM mapping stays symmetric
    # if someone wires in a real model later.
    "verifier": [{"note": "verify_attribution() runs the real check in code"}],
}

_call_index: dict[str, int] = {"planner": 0, "executor": 0, "verifier": 0}


def _mock_llm_call(role: str, prompt: str) -> dict[str, Any]:
    """Return the next canned response for this role. prompt ignored in stub."""
    idx = _call_index[role]
    responses = _CANNED_RESPONSES[role]
    response = responses[min(idx, len(responses) - 1)]
    _call_index[role] = idx + 1
    return json.loads(json.dumps(response))  # deep copy


# ----------------------------------------------------------------------------
# Planner Agent
# ----------------------------------------------------------------------------

class PlannerAgent:
    """Receives a new document. Produces a Plan (tool sequence plus escalation
    triggers). Does not call tools itself."""

    SYSTEM_PROMPT = """You are the Planner in a compliance document triage system.
Given a new document, produce a Plan that names the exact tool call sequence the
Executor should run. Available tools: extract_entities, classify_document,
propose_routing. Plan must run extract before classify, classify before propose.
List the conditions that should trigger escalation instead of proposal. Do not
call tools yourself. Plan only."""

    def __init__(self, audit: AuditLog):
        self.audit = audit
        self.plan_log: list[str] = []

    def run(self, document_id: str, chunks: list[dict[str, str]]) -> Plan:
        self.audit.record("planner", "agent_start",
                          {"document_id": document_id, "chunk_count": len(chunks)})
        raw = _mock_llm_call("planner", f"{self.SYSTEM_PROMPT}\nDoc: {document_id}")
        plan = Plan(
            document_id=document_id,
            steps=[PlanStep(**s) for s in raw["steps"]],
            expected_artifacts=list(raw["expected_artifacts"]),
            escalation_triggers=list(raw["escalation_triggers"]),
        )
        self.plan_log.append(f"plan for {document_id}: {len(plan.steps)} steps")
        self.audit.record("planner", "plan_emitted",
                          {"steps": [s.step_id for s in plan.steps],
                           "triggers": plan.escalation_triggers})
        return plan


# ----------------------------------------------------------------------------
# Executor Agent
# ----------------------------------------------------------------------------

class ExecutorAgent:
    """Consumes a Plan, runs the tool sequence, produces an ExtractionResult.
    Owns the extraction scratchpad."""

    SYSTEM_PROMPT = """You are the Executor in a compliance document triage system.
You receive a Plan from the Planner. Call tools exactly in the order the Plan
specifies. Produce an ExtractionResult with claims (each traceable to chunk +
source_span), a classification, and a routing proposal. You do not decide
trustworthiness; the Verifier does that. If the Verifier asks for a re-run of
a specific step, re-run only that step with the correction hint provided."""

    def __init__(self, audit: AuditLog):
        self.audit = audit
        self.scratchpad: dict[str, Any] = {}

    def run(self, plan: Plan, chunks: list[dict[str, str]],
            correction_hint: str = "") -> ExtractionResult:
        self.audit.record("executor", "agent_start",
                          {"document_id": plan.document_id,
                           "step_count": len(plan.steps),
                           "correction_hint": correction_hint})
        raw = _mock_llm_call("executor", f"{self.SYSTEM_PROMPT}\nhint:{correction_hint}")
        real_chunk_id = chunks[0]["chunk_id"] if chunks else "unknown_chunk"
        claims = [ExtractedClaim(chunk_id=real_chunk_id, **c) for c in raw["claims"]]
        result = ExtractionResult(
            document_id=plan.document_id,
            claims=claims,
            classification=raw["classification"],
            proposal=raw.get("proposal"),
        )
        self.scratchpad["last_claim_count"] = len(claims)
        self.audit.record("executor", "extraction_emitted",
                          {"claims": len(claims),
                           "domain": result.classification.get("domain")})
        return result


# ----------------------------------------------------------------------------
# Verifier Agent (verify_attribution does the real work)
# ----------------------------------------------------------------------------

class VerifierAgent:
    """Consumes an ExtractionResult. Runs verify_attribution on every claim.
    Approves, requests a re-run of one Executor step, or escalates to human.
    Verifier never approves its own proposal; the HITL gate still runs after."""

    SYSTEM_PROMPT = """You are the Verifier in a compliance document triage system.
You receive an ExtractionResult from the Executor. For every claim, re-read a
broader window of the source document around the cited source_span and check
whether the broader context supports the claim. If any deadline claim is
contradicted by the broader window, raise VerificationFailure and request a
re-run of the extraction step with a correction hint. Never approve your own
output; the human-in-the-loop gate still runs after you. Bail to human
escalation when a check fails twice in a row, the classification domain is not
in the routing table, or two deadline claims conflict."""

    BROADER_WINDOW_CHARS = 2000

    def __init__(self, audit: AuditLog):
        self.audit = audit
        self.check_results: list[ClaimCheck] = []

    def run(self, extraction: ExtractionResult, document_text: str,
            chunks: list[dict[str, str]]) -> VerificationResult:
        self.audit.record("verifier", "agent_start",
                          {"document_id": extraction.document_id,
                           "claims_to_check": len(extraction.claims)})

        checks: list[ClaimCheck] = []
        for claim in extraction.claims:
            check = verify_attribution(claim, document_text, chunks, self.BROADER_WINDOW_CHARS)
            checks.append(check)
            self.audit.record("verifier", "claim_check",
                              {"claim_id": check.claim_id, "passed": check.passed,
                               "reason": check.reason})
        self.check_results = checks

        # Conflict check: two different deadline ISOs is an auto-escalate.
        deadlines = [c for c in extraction.claims
                     if c.claim_type == "deadline" and c.deadline_iso]
        if len({d.deadline_iso for d in deadlines}) > 1:
            self.audit.record("verifier", "conflict_detected",
                              {"deadlines": [d.deadline_iso for d in deadlines]})
            return VerificationResult(
                document_id=extraction.document_id, checks=checks,
                approved=False, rerun_step_id=None, escalate_to_human=True,
                escalation_reason="two extracted deadlines conflict",
            )

        failed = [c for c in checks if not c.passed]
        if failed:
            # All claim types map to the same extract step in this plan shape.
            failing_claim = next(c for c in extraction.claims
                                 if c.claim_id == failed[0].claim_id)
            rerun_step = "s1_extract"
            self.audit.record("verifier", "rerun_requested",
                              {"rerun_step_id": rerun_step,
                               "failed_claim_id": failed[0].claim_id,
                               "failed_claim_type": failing_claim.claim_type})
            raise VerificationFailure(step_id=rerun_step, checks=checks)

        # Routing-miss guard.
        if extraction.proposal and extraction.proposal.get("proposed_owner") == "unassigned":
            return VerificationResult(
                document_id=extraction.document_id, checks=checks,
                approved=False, rerun_step_id=None, escalate_to_human=True,
                escalation_reason="routing table has no owner for this domain",
            )

        self.audit.record("verifier", "approved_for_hitl",
                          {"passing_claims": len(checks)})
        return VerificationResult(
            document_id=extraction.document_id, checks=checks,
            approved=True, rerun_step_id=None, escalate_to_human=False,
            escalation_reason=None,
        )


# ----------------------------------------------------------------------------
# verify_attribution: real code, not prose
# ----------------------------------------------------------------------------

def verify_attribution(
    claim: ExtractedClaim,
    document_text: str,
    chunks: list[dict[str, str]],
    broader_window_chars: int,
) -> ClaimCheck:
    """Re-read the broader window around the claim's cited span and decide
    whether the broader context supports the claim.

    Pass conditions: the cited value string appears inside the broader window,
    and (for deadline claims) no contradicting section heading appears that
    would re-attribute the deadline to a different risk area.

    Re-run triggers: the cited value string does not appear in the broader
    window, or (for deadline claims) the broader window contains a heading
    that would re-attribute the deadline.
    """
    chunk = next((c for c in chunks if c["chunk_id"] == claim.chunk_id), None)
    if chunk is None:
        return ClaimCheck(claim_id=claim.claim_id, passed=False,
                          reason=f"chunk_id {claim.chunk_id} not found",
                          broader_context_excerpt="")

    chunk_text = chunk["chunk_text"]
    chunk_start = document_text.find(chunk_text)
    if chunk_start < 0:
        broader = chunk_text
    else:
        lo = max(0, chunk_start - broader_window_chars)
        hi = min(len(document_text), chunk_start + len(chunk_text) + broader_window_chars)
        broader = document_text[lo:hi]

    excerpt = broader[:400]

    # Check 1: verbatim presence of the claim's value in the broader window.
    if claim.value not in broader:
        return ClaimCheck(
            claim_id=claim.claim_id, passed=False,
            reason=f"claim value '{claim.value[:60]}' not found in broader window",
            broader_context_excerpt=excerpt,
        )

    # Check 2: for deadline claims, scan for re-attributing section headings.
    if claim.claim_type == "deadline":
        contradicting_headings = [
            "Third-Party and Vendor Oversight",
            "Vendor Risk",
            "Capital Adequacy",
            "Tier 1",
        ]
        heading_hits = [h for h in contradicting_headings if h in broader]
        if heading_hits and "correspondent banking" not in broader:
            return ClaimCheck(
                claim_id=claim.claim_id, passed=False,
                reason=f"broader window suggests re-attribution to {heading_hits[0]}",
                broader_context_excerpt=excerpt,
            )

    return ClaimCheck(
        claim_id=claim.claim_id, passed=True,
        reason="value present in broader window; no contradicting heading",
        broader_context_excerpt=excerpt,
    )


# ----------------------------------------------------------------------------
# Final artifact builder and main orchestration loop
# ----------------------------------------------------------------------------

def build_final_artifact(document_id: str, extraction: ExtractionResult,
                         verification: VerificationResult) -> dict[str, Any]:
    if verification.escalate_to_human:
        status = "ESCALATED, AWAITS HUMAN DECISION (no routing proposed)"
    else:
        status = "PROPOSED, AWAITS HUMAN APPROVAL"
    return {
        "status": status,
        "document_id": document_id,
        "classification": extraction.classification,
        "proposal": extraction.proposal if not verification.escalate_to_human else None,
        "claims": [asdict(c) for c in extraction.claims],
        "verification": {
            "approved": verification.approved,
            "escalate_to_human": verification.escalate_to_human,
            "escalation_reason": verification.escalation_reason,
            "checks": [asdict(c) for c in verification.checks],
        },
        "reviewer_instructions": (
            "This output is a draft for human review. Do not act on the proposal until a "
            "human reviewer has approved it. Every claim carries a source_span and a "
            "Verifier check; verify the quoted text before approving."
        ),
    }


MAX_EXECUTOR_RERUNS = 1


def run_pipeline(document_id: str, document_text: str,
                 chunks: list[dict[str, str]]) -> dict[str, Any]:
    """Planner -> Executor -> Verifier -> (optional rerun) -> HITL gate."""
    audit = AuditLog(document_id=document_id)
    planner = PlannerAgent(audit)
    executor = ExecutorAgent(audit)
    verifier = VerifierAgent(audit)

    plan = planner.run(document_id, chunks)
    audit.record("orchestrator", "handoff",
                 {"from": "planner", "to": "executor", "artifact": "Plan"})

    extraction = executor.run(plan, chunks, correction_hint="")
    audit.record("orchestrator", "handoff",
                 {"from": "executor", "to": "verifier", "artifact": "ExtractionResult"})

    reruns = 0
    verification: Optional[VerificationResult] = None
    while True:
        try:
            verification = verifier.run(extraction, document_text, chunks)
            break
        except VerificationFailure as vf:
            if reruns >= MAX_EXECUTOR_RERUNS:
                audit.record("orchestrator", "rerun_budget_exhausted",
                             {"rerun_count": reruns, "last_failed_step": vf.step_id})
                verification = VerificationResult(
                    document_id=document_id, checks=vf.checks,
                    approved=False, rerun_step_id=None, escalate_to_human=True,
                    escalation_reason="verification failed after rerun budget exhausted",
                )
                break
            reruns += 1
            audit.record("orchestrator", "handoff",
                         {"from": "verifier", "to": "executor",
                          "artifact": "rerun_request", "step": vf.step_id})
            extraction = executor.run(plan, chunks,
                                      correction_hint=f"re-read for {vf.step_id}")
            audit.record("orchestrator", "handoff",
                         {"from": "executor", "to": "verifier",
                          "artifact": "ExtractionResult", "rerun": reruns})

    assert verification is not None
    final = build_final_artifact(document_id, extraction, verification)
    final["audit_log"] = [asdict(ev) for ev in audit.events]
    audit.record("orchestrator", "hitl_gate", {"status": final["status"]})
    return final


# ----------------------------------------------------------------------------
# Demo entry point
# ----------------------------------------------------------------------------

def main() -> None:
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    document_text = (
        "Per FinCEN advisory 2026-07, firms engaged in correspondent banking onboarding "
        "must update their customer due diligence policy to reflect the new jurisdiction "
        "risk rating by no later than 15 July 2026. Failure to comply may result in "
        "enforcement action under 31 CFR 1010."
    )
    chunks = [{
        "chunk_id": f"{doc_id}_chunk_01",
        "chunk_text": document_text,
        "document_type_hint": "regulatory_filing",
    }]

    result = run_pipeline(document_id=doc_id, document_text=document_text, chunks=chunks)

    print("\n" + "=" * 72)
    print("FINAL ARTIFACT")
    print("=" * 72)
    printable = {k: v for k, v in result.items() if k != "audit_log"}
    print(json.dumps(printable, indent=2, default=str))
    print(f"\n[stub complete; {len(result['audit_log'])} audit events recorded]")


if __name__ == "__main__":
    main()
```

## Honoring the Spec Constraints Explicitly

**Human-in-the-loop is non-negotiable.** Every tool description says "propose, do not act." The final artifact is labeled "PROPOSED, AWAITS HUMAN APPROVAL" in plain text, not a subtle confidence score. The router emits a proposal even when it is fully confident, because full confidence is not authority.

**Documents are unstructured.** The chunking strategy, the overlap, the broader-window verify step, and the source_span anchors are all designed around the "buried in paragraph 14" case. The agent does not rely on headers, tables of contents, or consistent terminology.

**No greenfield infrastructure.** S3 or Azure Blob for document storage (whichever the firm already uses), OpenSearch or Azure AI Search for retrieval, DynamoDB or Cosmos for the audit log, Lambda or Azure Functions for the loop runtime. All services the firm already runs. No Kafka, no Snowflake, no vector database as a prerequisite.

**Audit trail.** Every tool call, every tool response, every LLM message, and the taxonomy and routing-table versions are written to an append-only audit store keyed by document ID. A regulator can ask "why was this routed to Vendor Risk?" and get a complete answer, including the exact source text, the taxonomy version, and the model version used.

**Four-week first phase, two engineers.** Week one: ingestion, chunking, and the extract tool with audit logging. Week two: classify and propose, wired to a test set of 50 documents pulled from the firm's last quarter. Week three: human-review UI (a thin web page that shows proposal plus source spans plus approve or reject buttons), plus the routing-table YAML and taxonomy YAML. Week four: drift check, evaluation harness, and a read-only demo for the Head of Compliance on live-ish documents. No training, no fine-tuning, no new infra to provision. Everything runs on the firm's existing AWS or Azure footprint.
