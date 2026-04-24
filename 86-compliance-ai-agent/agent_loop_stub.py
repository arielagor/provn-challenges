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
