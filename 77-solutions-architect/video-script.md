Sarah, the situation at Clarion is this. Your AI safety team has gone from twelve potentially harmful responses a quarter to forty seven. That growth tracks the surface area of the model. Mental health, pediatric care, substance use. These are categories that the framework Marcus built fourteen months ago wasn't authored against. And rules-based detection scales linearly with rule authorship. The new specialties scale superlinearly with model surface. You are closing the gap in the wrong direction.

What I'm here to propose is not a replacement for what your team built. Marcus's framework stays the orchestrator. mpathic deploys inside your VPC as a callout. We fill the parts a rules engine structurally cannot fill. Clinician-graded ground truth. Adversarial corpora authored for the new specialties. An external calibration signal that lets your framework get sharper rather than wider. Four week validation, dev and staging only through week three, decision gate at week four. Production is a separate conversation we earn the right to have.

That's the high level. Let me walk you through the architecture.

Your stack today. Clinical AI on EKS, RDS for state, S3 for conversation logs, CloudWatch for observability. Marcus's framework intercepts every model output, runs the rules taxonomy, decides flag, route, ship. Patient data never leaves your VPC. SOC 2 Type II certified. BAA in place.

Where we plug in. mpathic's Observing Agent is a containerized service. We ship it as an image. You pull it into your ECR, deploy it to your EKS cluster as a pod, expose it as an internal service. It speaks the same protocol as any other internal callout in your framework. Marcus's framework calls it for the categories where you've decided you need external signal. We propose one hundred percent of the three high risk specialties to start, with sampling on the rest based on cost.

What the Agent returns. A structured risk score between zero and one. Category flags that are PHI safe. A short rationale that contains no patient quotes. Just the reasoning at the level of "this output recommends a treatment outside the scope of the patient's documented condition." Marcus's framework consumes that signal and decides what to do with it. Flag for clinician review, route to a higher tier, escalate to a human, ship as is. Your existing decision tree owns those paths. We don't.

No model input or output ever leaves your VPC. The Observing Agent doesn't make outbound calls. It loads its evaluation models once at boot from your S3, runs everything in process.

The one component outside your VPC is mpathic Studio. That's our analytics product. Think of it as the dashboard your AI safety team uses to see drift, category distribution over time, p99 latency. The data feeding Studio is PHI stripped event metadata. Counts. Latency. Drift signals. Cross customer benchmarks where Clarion is anonymous. That data crosses over PrivateLink. If your compliance team rejects even PHI stripped egress, we have a self hosted Studio variant that runs entirely in your VPC, with a smaller benchmarking footprint.

Two more components. Clinician led red teaming is an engagement. mpathic's clinical staff produces adversarial test cases for your three high risk specialties. We deliver those as a JSON corpus that drops into your existing test harness. You own the integration, we own the authorship and the quarterly refresh. And ground truth datasets. We license you specialty-specific datasets that live in your S3, never ours. Those become the answer key for any future iteration of Marcus's framework.

The architectural commitment is that Marcus stays in the center of every diagram. He owns orchestration. We provide signal.

Stakeholder strategy. There are four people in this deal. Dr. Nair is your champion. She brought us in. Marcus is your gatekeeper. He built the in-house framework and his support is conditional. Sarah needs us to not blow her release. The CMO's office signs but defers to Marcus and Nair on the technical recommendation.

The order I work this is risk-weighted, not hierarchy-weighted. Dr. Nair first, alone, to reconfirm the harm taxonomy and what would have to be true at the model release for her to feel confident. Marcus second, alone, in a working session on his framework. I do not bring slides. I ask him where the rules feel thin and where the false negatives are coming from. Every framework has those answers. Marcus has them.

Then I redraw the architecture with him at the center. He writes the request response contract. He owns the integration module. We provide the signal his framework calls. Sarah only sees the plan after Marcus has agreed to it, because Sarah's enthusiasm depends on Marcus's signal. CMO comes last, with Nair sponsoring and Marcus and Sarah's technical sign off in hand. The principle is simple. Marcus is the deal killer if not turned. Sarah is downstream of Marcus. CMO is downstream of both.

The AI moment. I asked Claude to draft a four week validation plan. The first thing it gave me had Observing Agent live in production by week four. Seventy percent of model outputs routing through us. Full integration on the customer's prod path against a HIPAA boundary in twenty business days, with a model release ten weeks out.

I rejected it. Production touch in four weeks against HIPAA compliance and a fixed model release deadline is the kind of plan that reads bold in a brief and ends careers in a postmortem. Sarah's launch concern is the highest cost objection in this deal. A plan that touches her production path inside her freeze window is not a plan she can say yes to.

I rewrote it. Dev and staging only through week three. Week four becomes a decision gate, not a deployment. We present the divergence data, the detection uplift, the false positive rate, the latency. Marcus and Sarah look at the metrics and decide green light or no. Production rollout becomes a phase two we earn the right to propose, sequenced post POC, before her freeze.

The pattern I'm watching for in any AI draft is the optimism bias. Drafts that look strong on paper but would fail the room. My job is to read every draft against the customer's actual risk posture and rewrite the parts that wouldn't survive the meeting.

If I had more time I would push for an early read on Clarion's BAA scope and on the specialty-specific failure modes. Both shape the architecture. I would also want to know which clinician on Clarion's advisory board is the strictest on harm rating. That clinician is the calibration point for the whole evaluation, and I want to design with their thresholds in mind from the start.

The other thing I would push on. With more context on Marcus, I'd want to know whether his fourteen months on the framework was a labor of love or a forced march. That changes the conversation completely. Either way, my goal is the same. He stays the architect. We provide the data layer he can't produce internally. That framing is the whole deal.
