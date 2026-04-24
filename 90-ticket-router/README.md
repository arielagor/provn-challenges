# Challenge 90 — Build a Support Ticket Router That Scales

**Role archetype:** Junior SWE  
**PROVN page:** https://provn.co/challenge-details/90  
**Submitted:** 2026-04-23

## Brief (paraphrased)

Write a Python function that routes inbound support tickets to one of five queues (escalation, account management, billing, technical, general) based on customer tier, urgency, and content keywords. Rules have hard-vs-soft precedence (enterprise + urgent always goes to escalation, regardless of keyword match). Include 2+ unit tests and document the edge cases without AI assistance.

## In this folder

| File | What |
|---|---|
| [`ticket_router.py`](ticket_router.py) | Primary deliverable. Python 3, 2 embedded test cases, handles all 5 categories with documented precedence. |
| [`video-script.md`](video-script.md) | 3-minute video walkthrough spoken transcript |
| [`ai-usage-log.md`](ai-usage-log.md) | PROVN-required AI usage disclosure. Section B (Edge Case Reasoning) written without AI per spec. |

## Video

[Watch the 3-minute walkthrough](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/90-video-final.mp4)

## Grader feedback

Uniformly positive. No open issues.
