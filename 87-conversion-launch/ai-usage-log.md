# Challenge 87 README

## Section A: Written analysis

Two problems landed on the same desk in the same week, and they look separate until you hold them next to each other for a minute.

Trial conversion fell from 18% to 11%. Coach ships in six weeks. The tempting move is to treat these as parallel workstreams and assign one to growth and the other to marketing. That is the wrong read. They are the same problem wearing two hats.

Conversion is falling because 76% of trial users never reach the Pipeline Health dashboard inside 72 hours. That dashboard is where Fieldline stops looking like a CRM add-on and starts looking like a system of record for deal risk. Coach, when it ships, is a layer on top of Pipeline Health. If users do not get to Pipeline Health, Coach has no surface to land on. A Coach launch into a funnel that loses three quarters of its trial users in the first 72 hours is a launch into a leaky bucket with a more expensive bucket.

So solving activation helps Coach twice. It raises the denominator of trial users who ever see the product Coach sits inside. And it proves the value of Pipeline Health to the buyer segment, second-line sales managers, who are the same buyer Coach is for. Coach then does not need to re-convince anyone that Fieldline sees their pipeline. It only needs to convince them that Fieldline can act on what it sees.

The inverse is also true. A good Coach launch raises the ceiling on what activation means. Pre-Coach, the activation moment is "I saw my pipeline with risk flags." Post-Coach, it becomes "Coach told me which deal to look at this afternoon and why." That is a stronger first-session hook and a better thing to optimize an onboarding flow toward. So the Week 1 activation work we do now becomes the on-ramp for Coach in Week 6.

What got deprioritized, and why.

Email engagement at 4% click-through is real, and the marketing team of four will want to run a re-engagement sequence. I am pushing that to a smaller workstream behind activation, because email is a distribution channel for a product moment that is broken. Fix the product moment, then fix the channel. Running a big email experiment now inflates the cost of the leak.

Pipestack pricing at $79 is a real competitive pressure. I am not touching price this cycle. A price cut signals weakness and locks in lower revenue per seat at the exact moment we are about to launch a feature that justifies the price. Coach is the pricing answer, not a discount. We respond to Pipestack by moving faster on AI, not by moving cheaper on the core.

What I am doing: one experiment to raise activation, a six-week Coach launch that uses activation as its on-ramp, and a sales enablement track that rewrites how nine reps talk about Fieldline against Pipestack. Everything else waits.

## Section B: GTM timeline and alignment plan

### Six-week plan to launch

**Week 1.** Kick off activation experiment A1 (guided Pipeline Health onboarding). Instrument the 72-hour activation funnel end to end in product analytics. Write Coach positioning v1 and pressure-test it with two reps and one existing customer. Start a shared Slack channel for the launch with product, sales, marketing, and engineering.

**Week 2.** Ship the onboarding A/B behind a flag. Lock Coach positioning v2 with VP Marketing sign-off. First sales enablement session with the nine reps, focused on Pipeline Health as the activation moment and how to reference it in discovery. Draft launch page copy and Coach demo script.

**Week 3.** Read the first week of A1 data. If activation is trending up, double the rollout. If flat, diagnose before adding more traffic. Beta Coach with five friendly customers, all second-line sales managers. Start building the launch page, the in-product announcement, and the customer-facing one-pager. Security review and audit logging for Coach prompts.

**Week 4.** Close the loop on beta feedback. Second sales enablement session: full Coach demo, five objection responses, competitive talk track against Pipestack. Draft the launch-day email sequence and a two-week post-launch nurture flow. Pricing decision locked: Coach included in current tier, no price change.

**Week 5.** Dress rehearsal. Full Coach demo to the go-to-market team. Walk the launch-day checklist. Finalize customer stories from beta. Ship the launch page to staging. Engineering gates Coach behind the launch flag. Sales starts teasing Coach in late-stage deals as "launching in two weeks" to block Pipestack in active evals.

**Week 6.** Launch. In-product announcement, email sequence, launch page live, press briefing, customer webinar. Activation experiment A1 graduates or kills. Sales moves fully to Coach-led positioning. Daily standup for the first five days post-launch to catch fires.

### Three named cross-functional dependencies

One. Product analytics instrumentation of the 72-hour activation funnel, owned by product and engineering, needed by end of Week 1. Without this, experiment A1 is unmeasurable and the whole brief collapses.

Two. Coach API rate-limit and audit-logging work, owned by engineering, needed by end of Week 3. Coach talks to customer CRMs and reads live pipeline. If rate-limiting or logging is not in place by beta, we risk a customer data incident in Week 4.

Three. Sales enablement time commitment, owned by VP Sales, needed across Weeks 2, 4, and 6. The nine reps need three 90-minute sessions, not a recorded video. If VP Sales pulls reps out of these sessions to chase pipeline, they will still be pitching "pipeline visibility" the day Coach launches.

### Sales enablement brief (for the nine reps)

Before launch, every rep needs: a 30-minute Pipeline Health activation story they can tell in discovery, a five-minute Coach demo they can run live off their laptop, a one-page competitive card versus Pipestack, five pre-written responses to Pipestack's price objection, and a list of their top ten accounts pre-tagged as "Coach-fit" based on the ICP (second-line sales manager, 100 to 400 person company, CRM in place).

Positioning shift versus Pipestack. Old pitch: Fieldline gives you pipeline visibility. New pitch: Fieldline is the only pipeline tool that coaches your reps in the moment the deal slows down. Pipestack shows you the pipeline. Coach acts on it. When a prospect brings up Pipestack's price, the rep should not defend the gap. The rep should ask what the prospect's managers currently do with the visibility Pipestack provides. The answer is almost always "nothing automated," and that is the wedge.

### Contingency: Pipestack announces AI in Week 3

Specific changes, not a rewrite.

First, do not move the launch forward. Our feature is ready, theirs is rumored. Beating them to market by a week is worth less than a clean launch.

Second, sales starts teasing Coach in active evals in Week 3 instead of Week 5. We do not wait. Reps get a two-paragraph "here is what Coach does that Pipestack's announcement does not" leave-behind by end of Week 3, written by marketing and signed off by VP Sales in 48 hours.

Third, Week 4 enablement flips from "Coach demo" to "Coach versus Pipestack AI demo," side by side on real pipeline data. This costs one extra prep day. It is worth it.

Fourth, the launch-day message reframes from "Fieldline's first AI feature" to "the AI coaching layer that actually sits inside your pipeline." Positioning was already built around Coach acting on Pipeline Health, so this is a phrasing change, not a strategy change. That is the point of grounding Coach in Pipeline Health from the start. Pipestack cannot copy that story without rebuilding their product.

Everything else holds.

## Section C: AI usage log

Three honest interactions. Claude did the drafting, Ariel steered.

**One. Funnel diagnosis framing.** Ariel asked Claude to pick one of the three conversion problems and defend it, not list all three. First draft from Claude leaned toward the competitive Pipestack problem because it felt like the most urgent narrative. Ariel pushed back, pointing at the math: 3x conversion on 24% adoption is a bigger mechanical lever than 6 of 14 head-to-head losses on price. Claude rebuilt the diagnosis around activation and kept the other two problems as explicitly deprioritized second-order fights. Kept the revised version.

**Two. ICP specificity.** Ariel asked for an ICP a sales rep could actually use in conversation. Claude's first pass was generic: "VP of Sales at mid-market B2B companies." Ariel rejected that as useless for qualification. Claude rewrote it around the behavioral tell of a second-line sales manager who reviews pipeline Friday nights because one-on-ones pull from memory. Kept the behavioral version. Cut the generic titles.

**Three. Messaging voice.** Claude's first draft of launch messaging used product-centric language: "AI-powered coaching that surfaces deal insights in real time." Ariel rejected all of it as slop. Claude rewrote in buyer language: "stop coaching from memory," "your reps get better at the deal, not at using another tool." Kept both rewrites. Cut "AI-powered," "real-time," and "insights" from the doc entirely.
