# Video Walkthrough — Challenge 94

**Note on submission:** The "Video Walkthrough" slot for this challenge on provn.co lists its accepted formats as `.pdf, .doc, .docx, .rtf, .txt, .md`, not `.mp4`/`.mov`/`.webm`. The spec prose says to upload as MP4 or MOV, but the form's actual MIME filter rejects video uploads. This markdown is the workaround: the video itself is linked below, and the full spoken transcript is reproduced so the grader can score communication without needing to download the file.

## Primary video link (anyone with the link can watch, no login required)

Direct HeyGen video file (720x1074 portrait, 2:35, 66.7 MB):
`https://files2.heygen.ai/aws_pacific/avatar_tmp/a7b1bbb0c4b94aa18681c35dec4409ad/c2a64160cd1c48d19a686bde86c9b129.mp4?Expires=1777593642&Signature=YbktpcnqPVwzQlPXEHp5KFLCno0J3wDr3-nVRXWaapiFTnJI~yGW~qesyAwx0pvJQbqfnjpbmH9VDPSxHNNOqOaufkWTfk2cVWXLCVJQ9aC-rIQUhY3aF644ttOrzQPVinUaEFFBLqLK8s9kTXny0jvCk11nuCe3~EOL6B8gHF3zC-~qF2Gp1Z-ZdM5bhugNWlnizszCOiZqG5N3qB7YbijbIUOu5eQcIh1P1EgsLfV7mzoTTQLFq7cI6X9Tc71V2-ulYkoipOVqqTu5mkAetQQ-gHdEd8AhtG6ybbP9jR~Uo6C5alQaRQNxNKElbBFz-NXw-aY755wTuICCKZtlNg__&Key-Pair-Id=K38HBHX5LX3X2H`

HeyGen project page (requires the submitter's login, shown here for provenance):
`https://app.heygen.com/videos/c2a64160cd1c48d19a686bde86c9b129--c2a64160cd1c48d19a686bde86c9b129`

Thumbnail preview:
`https://resource2.heygen.ai/video/c2a64160cd1c48d19a686bde86c9b129/gif.gif`

Video ID: `c2a64160cd1c48d19a686bde86c9b129`. Rendered via HeyGen, dimension 720x1074 portrait, duration 155.25 s.

## Full spoken transcript

The problem is not that a dbt model broke. It is that a sales rep found out first, after quoting a customer on the stale number. Fourteen dbt models feed forty-plus Looker dashboards. Three failures last quarter, two reached sales. dbt, Snowflake, and Looker each have their own health signals and none cross over.

Two things beyond the pre-call notes. First, the $50K CTO budget is not the real ceiling. The CFO wants ROI framing above $35K, which puts her effective budget three thousand above Monte Carlo and ten thousand below us. Without CFO-ready language, she picks the cheaper tool on price alone. Second, fourteen models into forty dashboards is almost three per model. Reactive patching cannot work. The math forces upstream monitoring.

I walk her pains in the order she lives them. First, she finds out about failures from stakeholders. I show a failing dbt test, lineage lighting up three Looker dashboards, auto-pause so sales never sees the bad number. Second, two-person team. Connector-first setup and learned thresholds, so day two is a notification feed, not a configuration surface. Third, she has to sell her CFO. I show the incident ledger that writes her ROI case in her own data. Order matters. The first two pains earn the right to talk about the third. If I open on ROI, I sound like a vendor.

I take the price objection. Monte Carlo quoted thirty-two, we quoted forty-five. My response starts with a question back to her. On the two pricing decisions last quarter that went out on stale numbers, what was the dollar gap, and did those deals close? Whatever she says, thirteen thousand is almost certainly less than one of those mistakes. That reframes price from two invoices into one invoice against one incident.

Then I name the capability that pays for the delta. Lineage-based auto-pause. Monte Carlo alerts when a model breaks. We alert and we gate the downstream dashboards, so sales never sees the broken number. The delta is not a better alert. It is prevention.

I asked Claude to draft the implicit-constraint section. It returned three. Two were strong. The $35K CFO sub-cap and the 2.85x dashboard multiplier, both grounded in the numbers. The third was a sentence about Priya feeling reputational pressure from stakeholders. That reads well and proves nothing. It is a feeling claim, not a falsifiable constraint. I cannot test it on the call or demo against it. So I cut it and replaced it with the "she is the second engineer" constraint, from the literal phrasing: "two engineers, including me." That is a head-count fact with operational consequences. Every claim has to be testable. If Claude writes one that is not, I cut it.
