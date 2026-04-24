# Challenge 95 — Diagnose Silent Order Failures in a Live E-Commerce Pipeline

**Role archetype:** Senior SWE  
**PROVN page:** https://provn.co/challenge-details/95  
**Submitted:** 2026-04-23

## Brief (paraphrased)

You inherit an order confirmation service in production. Orders are silently failing in the queue. The starter code has five real bugs: (1) dangerous deserialization of untrusted SQS payloads, (2) a delete-before-send ordering bug that drops messages on SMTP failure, (3) no idempotency, (4) no retry logic for transient failures, (5) no dead-letter queue handling. Fix all five and produce a rollout + observability plan that would actually land safely in production.

## In this folder

| File | What |
|---|---|
| [`order_confirmation_service_fixed.py`](order_confirmation_service_fixed.py) | Primary deliverable. All 5 bugs fixed: safe `json.loads()` parsing, delete-after-send flow, DynamoDB-backed `seen_receipt_handles` for idempotency, exponential backoff retry (1s/2s/4s, 3 attempts), DLQ routing for poison pills with structured metadata. |
| [`order_confirmation_service.py`](order_confirmation_service.py) | Original broken starter (included for diff clarity). |
| [`alarms.yaml`](alarms.yaml) | CloudWatch alarms covering DLQ depth, retry rate, email send failures, processing latency — so a repeat of this incident pages someone within 5 minutes. |
| [`video-script.md`](video-script.md) | 4:41 video walkthrough spoken transcript (compressed from spec's 8-10 min target) |
| [`ai-usage-log.md`](ai-usage-log.md) | PROVN-required AI usage disclosure. Section B2 (Reasoning) written without AI per spec. |

## Video

[Watch the walkthrough](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/95-video-final.mp4)

## Grader feedback

Strong on v2. Covers observability (concrete alarm spec), rollout plan, and DynamoDB idempotency. One graded nit — video under spec's 8-10 minute target at 4:41. Kept compressed per Ariel's 3-minute rule; accepted trade-off.
