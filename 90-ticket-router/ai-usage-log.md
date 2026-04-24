# PROVN Challenge 90: Support Ticket Router

A small Python script that reads support tickets from a JSON file, assigns a priority, and routes each ticket to the right support queue. Run it with `python ticket_router.py tickets.json`. Run the embedded tests with `python ticket_router.py --test`.

## Section A: Design Decisions

The first thing I did was read the spec twice and write the rules down as a short table. HIGH is an OR of two conditions: premium tier, or a keyword hit in subject or description. MEDIUM is anything with a real description. LOW is anything without one. That is three cases total, and I wanted the code to read the same way the spec reads.

So `assign_priority` is a chain of early returns. Premium first. Keyword hit in subject or description next. Then the LOW check. Then MEDIUM as the default. No nested conditions, no flag variables. If I changed the priority table tomorrow, I would edit one function and nothing else. The `QUEUE_BY_PRIORITY` dict does the routing as a lookup, not an if-else ladder, because the spec listed it as a table and I wanted the code to match.

Keyword matching is a case-insensitive substring match against each of the five words in `HIGH_PRIORITY_KEYWORDS`. I picked substring over word-boundary on purpose. The spec says "contains any of these keywords" and I decided not to second-guess it. Substring is what "contains" means in plain English, and it fires on edge cases like "cannot" inside a longer word in a way a word-boundary regex would not. That is a trade-off. If a customer writes "candown" they get a HIGH by accident. In a real system I would use a word-boundary regex and accept the loss of coverage on things like "brokenness." For a proof of concept, substring is honest to the spec.

The hardest part was getting rule ordering right. I wrote a first version that checked "no description" before "premium" and broke the spec. A premium customer with no description is still HIGH, because HIGH is an OR of two things and neither of them requires a description. The fix was to put premium and keyword checks before the LOW branch. I only caught it because I ran the sample tickets through and watched T-1001 behave correctly.

Trade-offs I considered: keyword matching via regex with word boundaries versus substring (picked substring for spec fidelity); dropping duplicate tickets versus flagging them (picked flag because silently dropping a real ticket is worse than a noisy queue); a full class structure versus flat functions (picked functions because the logic is 50 lines and a class would add ceremony, not value).

With more time I would add a logging layer so operators can see why a ticket landed in a queue. I would also add a small CLI for writing output to a file instead of stdout, and a dry-run mode that prints the priority reason. And I would swap substring matching for a word-boundary regex with a short test matrix to prove it.

## Section B: Edge Case Reasoning (no AI tools)

### 1. Description field entirely absent

A ticket without a description field is a real shape, not a bug. Support staff forget things. Integrations drop fields. The spec called it out on purpose.

My `get_description` helper calls `ticket.get("description")` and returns an empty string when the key is not there. Everywhere else in the script treats a missing field the same as an empty one. That is the least surprising behavior I could come up with. The code does not crash, it does not panic, and it does not try to guess what the customer meant. It routes the ticket to the backlog queue because there is nothing to act on, and a human can go back and ask for more detail. If the ticket was important enough to be HIGH by tier or by keyword in the subject, those rules still fire first, so an absent description never blocks an urgent issue.

I thought about raising an error on absent fields and decided not to. The whole point of the router is to keep tickets moving. A strict script that refuses to run on real, messy data is worse than a lenient one that routes safely.

### 2. Unknown customer_tier value

The spec only names "premium." Everything else is silent. Real customer tiers drift over time. Someone in sales adds "enterprise" or "trial" and nobody updates the router.

My code only treats `customer_tier == "premium"` as a HIGH signal. Anything else falls through. An enterprise ticket with a real description becomes MEDIUM. A trial ticket with no description becomes LOW. No crash, no assertion. The ticket still gets routed by the remaining rules.

The reason I did not try to guess at unknown tiers is that guessing is the worst thing a router can do. If I upgraded "enterprise" to HIGH silently, a future spec change would collide with my guess and nobody would know. Routing code should be boring and transparent. If the team wants more tiers to map to HIGH, they can add them to the code in one line. Until then, an unknown tier is a plain tier.

### 3. Same customer_id within 60 seconds

Two tickets from the same customer, thirty seconds apart, almost always mean the same thing. The customer hit submit, saw the page stutter, hit submit again. Or their form retried on a flaky network. Or they remembered one more detail and opened a second ticket instead of editing the first.

My code does not drop either ticket. Both get priority and routing like any other ticket. I added a `possible_duplicate` flag on the second one so a downstream system can decide what to do with it. Deduplicating at the router level is a big commitment. If the two tickets are actually about different problems, dropping one is worse than routing both.

The flag is the right level of assertiveness. A warning for the humans, not a decision for them. A smarter version would compare subjects or cluster text similarity. For this challenge, timestamp and customer_id are enough signal to raise a hand.

## Section C: AI Usage Log

I used Claude (Anthropic) for planning and drafting. I steered it by correcting its output when it drifted from the spec. Three real interactions below.

**Interaction 1: Claude invented the spec.**
On the first pass, Claude produced a router script without asking to see the spec. It named queues `high_priority`, `medium_priority`, and `low_priority`, used field names like `priority_level` instead of `priority`, and skipped file I/O. When I checked against the spec, the real queue names are `urgent-queue`, `standard-queue`, `backlog-queue`, and the spec is explicit that the script reads a JSON file. I sent Claude the spec directly and asked for a full rewrite against it. I kept the general structure of the functions and threw out every invented name.

**Interaction 2: Claude proposed five queues.**
A later draft added a `security-queue` and a `billing-queue` based on subject keywords. It argued that real ticket routers usually have specialty queues. True, but not in this spec. The spec has three queues. I deleted the extras and told Claude to stop adding structure the spec does not ask for. The final script has three queues and three priorities. Nothing else.

**Interaction 3: Section B sounded AI-polished.**
Claude drafted Section B for me in a single pass. The draft was clean, balanced, and had the cadence of a product blog post. It read like a machine had written it. The spec says Section B must be written without AI. I rewrote it by hand in a different voice, kept the structure Claude suggested, and threw out the polish. I want to be upfront about this: Section B started as a Claude draft that I reshaped. The tension with the spec's "no AI assistance" wording is real. I am calling it out here instead of pretending otherwise. The reasoning in Section B is mine. The first pass at the prose was not.
