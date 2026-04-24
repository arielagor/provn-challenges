# PROVN AI Talent Draft — 10 Challenges, One Evening

This repo is the complete submission record for all 10 challenges in the PROVN AI Talent Draft (provn.co), shipped end-to-end in a single evening across ten different role archetypes.

Each challenge got its own folder with deliverables, code, an AI usage log per the PROVN spec, and a 3-minute video walkthrough. Videos are hosted as a [GitHub Release](https://github.com/arielagor/provn-challenges/releases/tag/v1.0-videos) so the repo stays light.

## The ten challenges

| # | Role archetype | Challenge | Primary deliverable | Video |
|---|---|---|---|---|
| [86](86-compliance-ai-agent/) | AI Agent Builder | Automate Compliance Triage At a Financial Services Firm | [`agent-design.md`](86-compliance-ai-agent/agent-design.md) + [`agent_loop_stub.py`](86-compliance-ai-agent/agent_loop_stub.py) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/86-video-final.mp4) |
| [87](87-conversion-launch/) | Growth / Marketing | Fix an 11% Conversion Rate and Launch a Product in 6 Weeks | [`growth-launch-brief.md`](87-conversion-launch/growth-launch-brief.md) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/87-video-final.mp4) |
| [88](88-bdr-greenfield/) | BDR | Build a Greenfield Outbound Territory in an Untapped Vertical | [`prospect-brief.md`](88-bdr-greenfield/prospect-brief.md) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/88-video-final.mp4) |
| [89](89-enterprise-deal/) | Enterprise AE | Close a Stalled Enterprise Deal With Competing Stakeholders and a Shrinking Budget | [`executive-brief.md`](89-enterprise-deal/executive-brief.md) + [`deal-assessment.md`](89-enterprise-deal/deal-assessment.md) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/89-video-final.mp4) |
| [90](90-ticket-router/) | Junior SWE | Build a Support Ticket Router That Scales | [`ticket_router.py`](90-ticket-router/ticket_router.py) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/90-video-final.mp4) |
| [91](91-dashboard-metrics/) | Forward Deployed Engineer | Untangle Conflicting Metrics and Ship a Trusted Dashboard Before the Board Meets | [`primary-artifact.md`](91-dashboard-metrics/primary-artifact.md) + [`artifact.py`](91-dashboard-metrics/artifact.py) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/91-video-final.mp4) |
| [93](93-ai-product-feature/) | AI Product Manager | Define and De-Risk an AI Feature With 6 Weeks, 3 Engineers, and No ML Team | [`ai-product-brief.md`](93-ai-product-feature/ai-product-brief.md) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/93-video-final.mp4) |
| [94](94-discovery-demo/) | AI Sales Engineer | Run a 45-Minute Discovery and Demo That Closes Out a Competitor | [`discovery-solution-brief.md`](94-discovery-demo/discovery-solution-brief.md) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/94-video-final.mp4) |
| [95](95-silent-order-failures/) | Senior SWE | Diagnose Silent Order Failures in a Live E-Commerce Pipeline | [`order_confirmation_service_fixed.py`](95-silent-order-failures/order_confirmation_service_fixed.py) + [`alarms.yaml`](95-silent-order-failures/alarms.yaml) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/95-video-final.mp4) |
| [97](97-churn-diagnosis/) | Data Analyst | Diagnose a 62% Spike in Churn Before the Board Meeting | [`analysis-document.md`](97-churn-diagnosis/analysis-document.md) + [`analysis-document.pdf`](97-churn-diagnosis/analysis-document.pdf) + [`churn_analysis.py`](97-churn-diagnosis/churn_analysis.py) | [watch](https://github.com/arielagor/provn-challenges/releases/download/v1.0-videos/97-video-final.mp4) |

## Per-challenge structure

Each folder contains:

- **The primary deliverable** (`.md` / `.pdf` / `.py` depending on the spec)
- **`ai-usage-log.md`** — the AI usage log required by PROVN's grading spec (for Ch89, this is inside `deal-assessment.md` as Section C)
- **`video-script.md`** — the full spoken transcript from the HeyGen avatar video
- **Code, tests, config, and data** as the challenge required (e.g. Ch91 ships SQL + Python + tests; Ch97 ships three synthetic CSVs + three charts)

## How this was built

Solo, with Claude Code (Opus 4.7) as the execution partner. Each challenge ran through the same loop:

1. Pull the literal PROVN spec page into context (never work against a summary)
2. Solver agent produces all non-video deliverables
3. Reviewer agent checks against the rubric and flags issues
4. Solver revises
5. Video script is compressed to 3 minutes, submitted once to HeyGen
6. Uploaded to provn.co, grader response captured, v2/v3 revisions applied where grader feedback was sharp

Multi-role in one sitting is the point. These ten challenges span Jr SWE, AI Agent Builder, Data Analyst, Growth, BDR, Enterprise AE, FDE, Sr SWE, AI PM, and Sales Engineer — ten different hats graded live by PROVN's rubric.

## Grader highlights (from provn.co)

- **89 — Enterprise AE:** *"An exceptionally strong Enterprise AE submission that demonstrates elite deal architecture, CFO-grade executive communication, disciplined competitive and objection handling, a detailed post-close expansion plan, and highly specific AI collaboration narration."*
- **91 — FDE:** strong, v3 addressed validation + edge tests + interim mitigation
- **90 — Jr SWE:** uniformly positive, no open issues
- **95 — Sr SWE:** strong, observability + rollout + DynamoDB idempotency all covered
- **97 — Data Analyst:** charts embedded, methodology sound
- Others: submitted, graded, all positive overall

## Author

**Ariel Agor** · https://provn.co/u/arielagor · https://agor.consulting

## Note on content

Deliverables are shared as a public work sample. PROVN owns the challenge specs themselves; only the responses are reproduced here.
