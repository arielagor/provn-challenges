# README, Challenge 93, Meridian AI Assistant

## Section A. Technical Constraint Assessment and Risk Register

**Top three constraints, in order of how much they bend the plan.**

**1. Data residency not yet cleared by legal.** Four enterprise accounts cannot have their data or queries sent to a hosted LLM until Meridian has a signed data handling agreement, and possibly an in-region or in-VPC deployment to match their contracts. The risk this creates is not just that those four accounts miss Phase 1. It is that the team tries to solve for them inside Phase 1, burns two weeks on in-VPC inference that cannot ship, and loses the other 246 accounts along with them. *Mitigation that changes the design:* split the cohort in the feature flag layer on day one. Ship only to non-residency accounts in Phase 1. Offer a written Phase 2 pathway to the four accounts, with a clearly-named gating condition (legal sign-off) rather than a promised date. Remove on-premise and in-VPC inference from the Phase 1 scope document so no engineer starts on it.

**2. No internal ML team, six weeks, three full-stack engineers.** The risk is that someone on the team, pattern-matching on the word "AI," starts evaluating open-source models, running benchmarks, or designing an eval harness that belongs to a 20-engineer team. Six weeks evaporates into research. *Mitigation that changes the design:* use one hosted LLM provider, one model, behind a narrow tool-calling contract. No evaluation beauty contest. No fine-tune. The only ML work Meridian does in Phase 1 is prompt and tool design. The architecture document names the provider and model by version and forbids substitution inside Phase 1.

**3. Trust cratered by the competitor's AI failure last year.** The risk is that we ship a plausible-sounding wrong answer into a finance workflow and become the follow-up headline. *Mitigation that changes the design:* every Assistant response renders the SQL it ran, the row count, and a confidence note. The model answers against filtered result sets, not raw tables, so even an unrelated hallucination cannot invent a number outside the result. A red-team pass of 50 seeded questions graded against a known-correct key becomes a ship gate in Milestone 2. Customer Success gets a runbook before any external user sees the Assistant, not after.

**Most likely cause of a phase slip: data residency.** Not because it is technically hard, but because it sits outside engineering's control. Legal timelines move at legal speed. Enterprise procurement teams re-review data handling agreements at their own cadence. Even with the cohort split, the four named accounts will ask the CPO weekly when their Assistant turns on, and the pressure to try to solve it inside Phase 1 will be continuous. The cohort split in design is the single most important mitigation, because it moves the residency problem off the critical path entirely. If we had instead tried to ship to all 250 accounts in Phase 1, the legal gate would have been the phase gate, and the slip would already be baked in.

## Section B. Stakeholder Communication Plan

**Engineering team at kickoff.** You have three people, six weeks, and four constraints. Treat the scope document as a contract, not a suggestion. The Assistant is a thin shell over the semantic layer with a hosted LLM doing tool selection and summary. We are not building a chat app, a memory layer, or an agent. If someone asks us to add cross-dataset joins, write-back, or in-VPC inference inside Phase 1, route them to me. What I need from you is honesty about the three risks I have named, weekly: integration surprises with the semantic layer, LLM latency under load, and any evidence that the red-team eval is not catching the failure modes we built it for.

**Enterprise customer asking when the AI works with their data.** We owe you the real answer, not the convenient one. Your data residency requirements are real and we will honor them. That means your Assistant turns on in Phase 2, not Phase 1, because Phase 1 routes queries through an external model provider and our legal team has not yet signed a data handling agreement that covers your contract. Phase 2 is the work to make the Assistant available to you under terms that match what you signed with us. We are not giving you a Phase 2 date tonight because the gating condition is legal sign-off and I will not promise a date I cannot keep. I will give you a written update every two weeks with the actual state of that work.

**Customer Success team fielding AI-accuracy anxiety.** Customers are asking you about accuracy because they watched a competitor ship a wrong financial summary last year and they do not want to be the next story. Here is what to tell them. Every Assistant answer shows the SQL it ran and the rows it read, so they can check the work. The Assistant only summarizes the result the query returned, not the whole database, so it cannot invent a number outside the result. Before any external user touches the feature, we run 50 seeded questions against known answers and gate the ship on the pass rate. If a customer hits a wrong answer, thumbs it down, and we review every thumbs-down weekly with PM and engineering in the same room. Tell them that. Then tell them that the safeguards are not a promise the Assistant will never be wrong, because no AI feature can make that promise. The promise is that they will see the work, they will be able to catch it, and we will be watching.

## Section C. AI Usage Log

**Tools used.**

Claude (Anthropic, model Opus 4.7, inside the Claude Code CLI). This was the only AI tool used on this challenge.

**What the tool was prompted for, and what the output was used for.**

Ariel passed the spec, the `feedback_plain_strange_voice.md` memory, and the challenge brief to Claude and asked Claude to produce the three deliverables end to end. Claude read the spec, read the voice guide, drafted the brief, the README, and the video script, checked for em-dashes, and reported word counts. Ariel set the scope, the strategic stance (cohort split, deferral of on-premise inference to Phase 2, which risks to treat as ship-gating), the voice constraint, and the review gate. Claude did the drafting inside those rails.

**Moment where AI output needed correction.**

On the first pass, Claude's scope section listed the Phase 1 cuts as a three-item bulleted list, which violated the plain-strange voice rule against defaulting to three-item lists. Claude caught this in self-review before the file was finalized and rewrote the section as continuous prose with a longer, varied list, keeping the cuts but removing the list-of-three shape. A second correction: the draft of the enterprise customer comms opened with "I hear you, and," which is exactly the kind of softening hedge the voice guide rules out. It was rewritten to open on substance ("We owe you the real answer, not the convenient one."). Both corrections were structural, not factual.

**Percentage estimate.**

Original thinking versus AI-assisted, on the finished artifact: roughly 40% original, 60% AI-assisted. Ariel owned the strategy (cohort split, Phase 2 pathway as the residency answer, three ship-gates in Milestone 2 and 3, the three outcome metrics framed around demand, value, and safety signals), the hard constraints (voice, no em-dashes, honest Section C), and the review gate. Claude owned the drafting, the spec-to-sentence tracing, the consistency pass across the three artifacts, and the voice enforcement. The strategic spine is Ariel's. The prose around it is Claude's, written inside Ariel's voice on Ariel's instruction.
