# Challenge 95: Silent Order Failures

## Section A: Diagnosis and Recommendation

The 4 to 6 percent silent failure rate is not one bug. It is five bugs in
a specific arrangement, and they compound.

The immediate cause of silent drops is ordering inside the message loop.
The consumer calls `sqs.delete_message()` first, then calls
`send_confirmation()`. SQS uses at-least-once delivery. The whole
reliability model rests on one rule: the consumer deletes only after the
work is done. If you delete first and the SMTP call raises on a network
blip, an expired TLS session, or a rate-limit from the mail relay, the
message is gone and the order is gone with it. There is no exception
handler wrapping the send, so the worker logs nothing, alerts on nothing,
and moves on. The queue drains, the dashboards stay green, and support
picks up the phone three hours later.

Two other defects turn a rare drop into a chronic 4 to 6 percent. There
is no retry, so any one-off SMTP hiccup kills the order permanently. There
is no DLQ routing, so poison-pill messages (bad JSON, missing fields) cycle
through visibility timeouts forever, holding capacity and masking the real
SMTP failures in the noise. Separately, the starter uses the arbitrary-code
eval builtin on the queue body. That is a remote-code-execution hole the
size of a truck. Fifth defect: no idempotency, so the bugfix path itself
can produce duplicate confirmation emails once retries and redelivery
enter the picture.

The recommended fix has five moves, all bounded by the four-week window.
Flip delete-after-send. Wrap send in try/except and add bounded exponential
backoff (3 attempts, 1s / 2s / 4s, no jitter because this is a single
consumer). Swap the eval builtin for `json.loads` and route parse errors to
DLQ on the first try. Validate required fields before SMTP; malformed
payloads also go straight to DLQ. Add a DynamoDB conditional-write
idempotency claim on `order_id` so a retry, a worker restart, or a scaled-up
second worker can never send a duplicate email for the same order.

I chose this over the alternative of a Lambda-plus-Step-Functions rewrite.
That would also solve it, but it is a multi-quarter migration that adds
new infrastructure. Constraint 3 rules it out. The small fix sits inside
SQS plus SMTP plus DynamoDB plus CloudWatch, which is already what the
team owns.

### Idempotency: chose Option A, DynamoDB

The earlier revision of this service used an in-process set keyed on
`ReceiptHandle`. That was wrong, and I want to say so plainly. A
ReceiptHandle is per-delivery, which means SQS issues a new one on every
visibility-timeout redelivery of the same message. A set of ReceiptHandles
does not catch the common production duplicate case at all. It only
catches within-handler-loop duplicates, which almost never occur. The
previous code comment over-claimed the protection.

The fix is `PutItem` against a DynamoDB table keyed on `order_id`, with
`ConditionExpression: "attribute_not_exists(order_id)"`. The first caller
to claim the order wins and sends. Every other caller gets a
`ConditionalCheckFailedException` and silently skips the send. The table
carries a 7-day TTL so it never grows unboundedly. DynamoDB is already on
the approved AWS list in constraint 1, so this does not add a new system
to the ops footprint. It adds one table.

What DynamoDB covers that the set did not: SQS redelivery after visibility
timeout, horizontal scale-out to two or more workers, and worker restarts
mid-batch. Those were the three holes in the previous story. They are all
closed now.

### Deployment safety: staged rollout with a kill switch

The service runs on ECS and processes every real customer order. Shipping
a change to it overnight with no staged rollout would be reckless, so the
plan has five stages and two explicit rollback triggers.

Stage one. Deploy the new code with `DLQ_ON_PARSE_ERROR=false` and
`desired-count=1`. The kill switch keeps the new DLQ routing path inert
for parse and validation errors; those continue to log-and-delete as they
did before. The DynamoDB idempotency claim is active, and the retry and
delete-after-send fixes are active, because those are the paths the silent
drops actually live in.

Stage two. Soak for 24 hours. Watch the CloudWatch alarm
`OrderConfirmation-DLQ-Depth-Above-Zero`, the consumer log rate, and the
DynamoDB `ConditionalCheckFailedRequests` metric to confirm dedupe fires
on redelivery. Confirm DB `confirmation_sent = true` rate returns to
baseline. Rollback trigger: if the dedupe metric stays at zero or the
confirmation rate does not recover, revert the ECS task definition to
the previous revision and investigate.

Stage three. Flip `DLQ_ON_PARSE_ERROR=true` via an ECS task-definition
update. Parse and missing-field errors now route to DLQ. Soak 24 more
hours. Rollback trigger: if the DLQ alarm fires more than twice in an
hour, flip the flag back to false inside five minutes. The flip is a
single task-definition parameter change, not a code deploy.

Stage four. Scale `desired-count` from 1 to 2. This proves the DynamoDB
claim works across workers. The second worker will see
`ConditionalCheckFailed` on any message the first worker already claimed.
Soak 12 hours. Rollback trigger: if any customer reports a duplicate
confirmation email, scale back to 1 and diagnose.

Stage five. Scale to target capacity. Remove the kill switch env var
from task definition (it defaults to false, which is safe but no longer
needed once the code has soaked). File a post-rollout review.

Rollback for any stage is a single command:

```bash
aws ecs update-service \
  --cluster orders \
  --service order-confirmation-service \
  --task-definition order-confirmation-service:PREV_REVISION
```

The kill switch pattern is slightly belt-and-suspenders with the staged
rollout, and that is on purpose. The flag gives us a mitigation that is
faster than a redeploy if the DLQ path starts flapping.

### Trade-offs and phase-two work

Risks remaining after the 4-week ship: no backpressure if the fulfillment
vendor slows down upstream, and no CloudWatch alarm yet on p99 confirmation
send latency. The DLQ-depth alarm is in `alarms.yaml` and ships with the
fix; the latency alarm is phase two. A scheduled DLQ replay tool that a
human runs at 2am instead of hand-crafting aws-cli calls is also phase two.

## Section B1: Incident Runbook

You are on-call. You have been paged. You have not worked on this service
before. Read top to bottom.

**Trigger.** PagerDuty alert from SNS topic `order-confirmation-oncall`,
which fires on the CloudWatch alarm `OrderConfirmation-DLQ-Depth-Above-Zero`.
This alarm goes to ALARM the moment a single message lands in the DLQ.
Every DLQ message represents a customer order whose confirmation email
failed to send after all retries. The alarm is intentionally tight. You
would rather wake a human for one failure than let twenty drift in quietly.

1. **Establish blast radius.** Query the order DB for orders placed in the
   last 2 hours with `confirmation_sent = false`:

   ```sql
   SELECT order_id, customer_email, created_at
   FROM orders
   WHERE created_at > NOW() - INTERVAL '2 hours'
     AND confirmation_sent = false
   ORDER BY created_at DESC
   LIMIT 100;
   ```

2. **Check queue depths.** Main queue and DLQ both.

   ```bash
   aws sqs get-queue-attributes \
     --queue-url $QUEUE_URL \
     --attribute-names ApproximateNumberOfMessages \
                       ApproximateNumberOfMessagesNotVisible

   aws sqs get-queue-attributes \
     --queue-url $DLQ_URL \
     --attribute-names ApproximateNumberOfMessages
   ```

   The alarm already told you DLQ depth is non-zero. The question now is
   whether main-queue depth is also growing (upstream surge, or the
   consumer is stuck) or near zero (the consumer is running but each
   message is failing cleanly to DLQ).

3. **Tail worker logs for the last 30 minutes.**

   ```bash
   aws logs filter-log-events \
     --log-group-name /app/order-confirmation-service \
     --start-time $(date -d '30 minutes ago' +%s000) \
     --filter-pattern "ERROR"
   ```

   Group by reason. The DLQ `reason` field classifies parse errors vs.
   SMTP exhaustion vs. missing fields.

4. **Immediate mitigation before a code fix deploys.** You have two
   escalating levers, in order of blast radius.

   Lever one: flip the kill switch if the DLQ alarm is being caused by
   a flood of parse errors (bad upstream payload format). Set
   `DLQ_ON_PARSE_ERROR=false` on the ECS task definition and redeploy.
   Parse errors go back to log-and-delete. This is a five-minute change.

   Lever two: pause the consumer entirely if the SMTP relay is down and
   the DLQ is filling with exhausted-retry entries. Messages are safe in
   the main queue for 14 days.

   ```bash
   aws ecs update-service \
     --cluster orders \
     --service order-confirmation-service \
     --desired-count 0
   ```

   If the bug is a recent deploy, roll back instead of pausing:

   ```bash
   aws ecs update-service \
     --cluster orders \
     --service order-confirmation-service \
     --task-definition order-confirmation-service:PREV_REVISION
   ```

5. **Manually replay DLQ messages once the service is healthy.**

   ```bash
   aws sqs start-message-move-task \
     --source-arn arn:aws:sqs:us-east-1:123456789:order-confirmations-dlq \
     --destination-arn arn:aws:sqs:us-east-1:123456789:order-confirmations
   ```

   The DynamoDB idempotency claim will prevent any duplicate emails for
   orders that were actually sent on a prior attempt. Safe to replay.

6. **Backfill orders confirmed dropped.** For orders from step 1 whose
   messages were already deleted without sending (the pre-fix legacy case),
   use the admin re-send endpoint. Keep a list of order IDs. Run it in
   batches so rate limits do not pile on.

   ```bash
   for id in $(cat dropped_order_ids.txt); do
     curl -X POST https://api.example.com/admin/resend-confirmation \
       -H "Authorization: Bearer $ADMIN_TOKEN" \
       -d "{\"order_id\": \"$id\"}"
   done
   ```

7. **Confirm recovery.** Wait 10 minutes after restart, rerun the step-1
   query. Confirmation rate should be back to baseline. Close only on DB
   evidence, not queue depth. The alarm will auto-resolve (the CloudFormation
   template sets OKActions to notify the same SNS topic) once DLQ depth
   drops back to zero.

8. **File a post-mortem.** Timeline, root cause, affected customer count,
   the fix that shipped, and the monitoring gap that let the regression go
   undetected.

## Section B2: Required Reasoning Question (written without AI assistance)

The failure mode I am most worried about with an AI assistant on this
class of problem is that it gives an answer that is locally correct and
globally wrong, and does it with full confidence.

Here is the concrete scenario. I ask the AI to fix the silent failure. It
reads the code, spots the delete-before-send ordering, and produces a diff
that flips the two calls. The diff compiles. A unit test that says "message
is not deleted when SMTP throws" passes. The AI writes a nice commit
message. I ship it. The 4 percent drop rate goes away. A week later support
is back on the phone, this time about customers getting three or four
copies of the same confirmation email. What the AI confidently produced
was a correct fix to bug 2 that activated a latent duplicate-email path,
because without idempotency, the SQS visibility-timeout retry mechanism
now sends the same email two or three times on any transient SMTP slow
response. The unit test did not catch it. Why would it. The test was for
the bug we were fixing, not the one the fix introduced.

How I catch that kind of answer before shipping. I read the diff with the
failure mode explicitly in my hand, not just the happy path. For every
change, I ask what happens on re-delivery. What happens on timeout. What
happens if two consumers pick up the same message. I do not trust a test
that passes in the direction of the fix I asked for. I write one test in
the direction I did not ask for. In this case, the adversarial test is
"the same message is delivered twice, count the SMTP calls, assert one."
That test will fail on any idempotency story that keys on a per-delivery
handle rather than on the stable order_id, and it will expose the gap
before the code ships.

The other check I run on any AI diff for a system with retry or delivery
semantics is a whiteboard-style enumeration. Success. Parse error.
Validation error. Transient send error. Permanent send error. Re-delivery
inside visibility window. Re-delivery across visibility window. Worker
restart mid-batch. Two consumers in a race. I put the AI's diff against
each row and ask if the outcome is what I want. An AI pass that quietly
drops one of those rows is the tell. That is where I stop and push back.

I am not certain this catches everything. It does not. It catches the
class of error where the AI has optimized for the specific instruction
and missed the system-level invariant. Given how easy these models make
it to produce plausible-looking code, I think that class is the one that
will keep growing.

## Section C: AI Usage Log

I want to be honest about how this work was done. Claude (Anthropic) did
most of the typing. I steered the direction, challenged framing, rejected
output that did not meet the bar, and pushed the grader feedback back
into the artifacts. The interactions below are the ones that actually
shaped what shipped.

### Interaction 1: the retry budget

I asked Claude to add a retry wrapper around the SMTP send. Its first
pass was a loop with no cap and a fixed 30-second backoff. I rejected it.
Thirty seconds per attempt with no cap holds the message past the SQS
visibility timeout, which causes duplicate processing. I told Claude the
constraint: retries must complete inside 30 seconds total so the message
stays inside the visibility window, and there must be a hard cap so we
are not retrying forever against a dead relay. Claude came back with 3
attempts at 1s / 2s / 4s, which is what shipped. I kept the numbers.
I also kept its suggestion to raise the last exception up to the caller
so the DLQ-routing decision lives in one place.

### Interaction 2: the idempotency trade-off (and my honest correction)

First pass, I asked Claude whether idempotency should key on ReceiptHandle
or on order_id. Claude explained that ReceiptHandles are per-delivery and
order_ids are stable across re-deliveries. I then asked Claude to recommend
a path and accepted its suggestion of the ReceiptHandle set for phase one
with DynamoDB as phase two. That was a mistake. I shipped the first draft
with a comment that over-claimed what the set protected against. The
grader did not flag it. I flagged it on my own re-read, because the word
"idempotency" does not mean what the set was actually doing. A ReceiptHandle
set catches within-handler-loop duplicates, which are vanishingly rare,
and misses the visibility-timeout redelivery case, which is the one that
matters. I went back and asked Claude to rewrite the path against
DynamoDB conditional write on order_id with a TTL, and to rewrite the
comment so it describes what is actually protected. That is what is in
the current file.

### Interaction 3: the DLQ payload

I asked Claude what fields to include in the DLQ message so a human at
2am could triage from the SQS console. It suggested original MessageId,
ReceiptHandle, a reason field, and the raw body. I accepted all four.
I also asked Claude what ordering to use: write to DLQ first or delete
from main queue first. Claude said DLQ-write first, delete-after, because
the DLQ write is the operation that can fail and you do not want a failed
DLQ write plus an already-deleted main-queue entry. I agreed and coded
it that way. I did not have to push back on that one; Claude got it right
on the first pass.

### Interaction 4: grader feedback loop

The first submission came back with three notes. Video was too short at
~2 minutes versus the 8 to 10 minute target. Observability was conceptual
only, no concrete alarm. No deployment-safety discussion at all. I read
the notes and drove all three back through Claude.

For the video I asked Claude to re-expand the script to a 5-minute target
(Ariel authorized one HeyGen re-render at that length) with deeper
self-awareness, strategic thinking, and a specific "what I would do
differently" reflection. The script in this folder is that re-expansion.

For observability I asked Claude to define a concrete CloudWatch alarm
on DLQ depth, shipped as infrastructure-as-code, with an SNS topic that
pages the on-call. That became `alarms.yaml`. I reviewed the thresholds
(Threshold 0, Period 60s, EvaluationPeriods 1) and accepted them. The
alarm is tight on purpose; one DLQ message is always a dropped order.

For deployment safety I asked Claude for a staged rollout that does not
move customer traffic on day one. It proposed the five-stage plan and the
`DLQ_ON_PARSE_ERROR` kill switch as a sub-five-minute mitigation lever
independent of a redeploy. I accepted both and asked Claude to thread the
kill switch into the code so it is a real variable, not just documentation.
That is the `os.environ.get("DLQ_ON_PARSE_ERROR", "false")` default in
the Python file.

### Interaction 5: the honesty edit

After the grader feedback round, I re-read Section A and decided the old
"ReceiptHandle is good enough for phase one" framing was not something I
was willing to defend on a live phone call with a staff engineer. I asked
Claude to redo Section A with the honest version: DynamoDB is the right
answer on day one, the old phase-one story was a shortcut I took under
time pressure, and the comment in the code was over-claiming. The rewrite
is what is in this file. I think the corrected version reads better and
is more defensible. It is also slightly embarrassing, which I think is the
right tone when the diagnosis got sharper after review.
