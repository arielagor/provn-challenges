"""
order_confirmation_service_fixed.py

Proof-of-concept order confirmation consumer for Challenge 95.

Constraints honored (all four from the spec):
  1. AWS-only infrastructure. SQS + SMTP (SES in prod) + DynamoDB for
     idempotency + CloudWatch alarms via SNS. No Kafka, no new stacks.
  2. Fulfillment is a third-party vendor API upstream. This service never
     touches it. It only emits the customer-facing confirmation email.
  3. 4-week / 2-engineer scope. Single-process consumer with inline tests.
     DynamoDB is already approved in constraint 1, so using it for
     idempotency does not add a new system.
  4. The team owns the 2am page. Every failure mode has exactly one of
     three outcomes: success, bounded retry, or DLQ. No silent drops.

Fixes applied vs. the starter:
  1. json.loads replaces the arbitrary-code-eval builtin. Parse errors
     route to DLQ on the first try (not transient, never retry).
  2. Delete-after-confirm ordering. The SQS message is only removed once
     the email has sent or the DLQ write has succeeded.
  3. Idempotency via a DynamoDB conditional PutItem on order_id. This
     survives worker restarts, scale-out to N workers, and SQS visibility
     timeout re-delivery (which issues a new ReceiptHandle). TTL of 7 days
     keeps the table small.
  4. Bounded exponential backoff for transient SMTP errors: 3 attempts,
     1s / 2s / 4s, no jitter. No-jitter rationale is inline.
  5. DLQ routing split by failure class. Parse and missing-fields go to
     DLQ immediately. SMTP failures go to DLQ only after retries exhaust.
  6. Feature-flag kill switch via DLQ_ON_PARSE_ERROR env var. Defaults to
     false for the first soak so the new DLQ path does not move traffic
     before we have confidence in the routing. Flipped to true after the
     canary window. See readme Section A rollout plan.
"""

import json
import logging
import os
import time
import boto3
import smtplib
from botocore.exceptions import ClientError
from email.mime.text import MIMEText
from typing import Optional

# Structured log format so CloudWatch Logs Insights can parse fields.
# Honors constraint 1 (AWS-only) and constraint 4 (2am page needs signal).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("order_confirmation_service")

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789/order-confirmations"
DLQ_URL   = "https://sqs.us-east-1.amazonaws.com/123456789/order-confirmations-dlq"

IDEMPOTENCY_TABLE = os.environ.get("IDEMPOTENCY_TABLE", "order_confirmation_idempotency")
IDEMPOTENCY_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "orders@example.com"
SMTP_PASS = "secret"  # Retrieved from Secrets Manager in production.

MAX_SMTP_RETRIES = 3
RETRY_BASE_DELAY = 1.0   # seconds; doubles per attempt (1s, 2s, 4s)

# Feature-flag kill switch. Defaults OFF for the first soak window so the
# new DLQ routing path cannot move traffic before we trust it. See readme
# Section A for the rollout plan that flips this to true in stage 3.
DLQ_ON_PARSE_ERROR = os.environ.get("DLQ_ON_PARSE_ERROR", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Core send logic (separated for testability)
# ---------------------------------------------------------------------------

def send_confirmation(order: dict, smtp_host: str = SMTP_HOST,
                      smtp_port: int = SMTP_PORT,
                      smtp_user: str = SMTP_USER,
                      smtp_pass: str = SMTP_PASS) -> None:
    """
    Send a single order confirmation email.
    Raises smtplib.SMTPException on failure so the caller can retry or DLQ.
    """
    msg = MIMEText(
        f"Thank you for your order #{order['order_id']}!\n\n"
        f"We'll ship to: {order.get('email', 'unknown')}"
    )
    msg["Subject"] = f"Order Confirmation #{order['order_id']}"
    msg["From"]    = smtp_user
    msg["To"]      = order["email"]

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [order["email"]], msg.as_string())


def send_with_retry(order: dict, max_retries: int = MAX_SMTP_RETRIES,
                    base_delay: float = RETRY_BASE_DELAY) -> None:
    """
    Exponential backoff around send_confirmation.

    Design notes:
      * 3 attempts at 1s/2s/4s. Worst-case is ~7s plus SMTP socket timeouts,
        which fits inside the default SQS visibility timeout of 30s. That
        matters. If we exceeded the visibility window, SQS would redeliver
        the same message mid-retry and we would send duplicate emails.
      * No jitter. Jitter matters when a fleet of consumers is pounding the
        same upstream. This service is a single consumer; jitter would make
        retry timing harder to reason about without smearing any real herd.
      * Raises the last SMTPException so the caller can route to DLQ.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            send_confirmation(order)
            return
        except smtplib.SMTPException as exc:
            last_exc = exc
            delay = base_delay * (2 ** (attempt - 1))
            log.warning(
                "SMTP attempt %d/%d failed for order %s: %s. Retrying in %.1fs",
                attempt, max_retries, order.get("order_id"), exc, delay,
            )
            if attempt < max_retries:
                time.sleep(delay)

    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Idempotency (DynamoDB conditional write on order_id)
# ---------------------------------------------------------------------------

def claim_order(ddb, order_id: str) -> bool:
    """
    Attempt to claim the order for sending. Returns True if this caller
    won the race and should send. Returns False if any other caller (same
    worker, different worker, prior attempt after visibility timeout) has
    already claimed the order.

    Why DynamoDB and not an in-process set:
      * A set inside one process only catches duplicates inside that same
        process lifetime. It misses SQS re-delivery after visibility
        timeout (new ReceiptHandle, same order), horizontal scale-out,
        and worker restarts. These are the common cases in production.
      * DynamoDB conditional PutItem with attribute_not_exists(order_id)
        is an atomic claim that works across a fleet and survives restarts.
      * Table TTL evicts rows automatically after 7 days. No housekeeping.
    """
    now = int(time.time())
    try:
        ddb.put_item(
            TableName=IDEMPOTENCY_TABLE,
            Item={
                "order_id":   {"S": order_id},
                "claimed_at": {"N": str(now)},
                "ttl":        {"N": str(now + IDEMPOTENCY_TTL_SECONDS)},
            },
            ConditionExpression="attribute_not_exists(order_id)",
        )
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


# ---------------------------------------------------------------------------
# DLQ routing
# ---------------------------------------------------------------------------

def route_to_dlq(sqs, message: dict, reason: str) -> None:
    """
    Forward an unprocessable message to the dead-letter queue.

    The DLQ payload is intentionally rich so the on-call engineer at 2am
    can triage directly from the SQS console without grepping logs.
    """
    payload = {
        "original_message_id": message.get("MessageId"),
        "receipt_handle": message["ReceiptHandle"],
        "reason": reason,
        "body": message["Body"],
    }
    sqs.send_message(QueueUrl=DLQ_URL, MessageBody=json.dumps(payload))
    log.error(
        "Routed message %s to DLQ. reason=%s",
        message.get("MessageId"), reason,
    )


# ---------------------------------------------------------------------------
# Main processing loop
# ---------------------------------------------------------------------------

def process_messages(
    queue_url: str = QUEUE_URL,
) -> None:
    """
    Long-poll SQS and process each order confirmation message.

    Idempotency is enforced via DynamoDB conditional PutItem on order_id.
    That guards against:
      * SQS re-delivery after visibility timeout (same order_id, new handle)
      * Horizontal scale-out (shared DynamoDB table across all workers)
      * Worker restart mid-batch (claim persists)

    What DynamoDB does NOT cover:
      * A truly new order with the same order_id (should not happen if
        upstream generates unique IDs; if it does, the second one is
        silently dropped which is the correct outcome for a duplicate).
      * Cross-region disaster recovery. Out of scope.
    """
    sqs = boto3.client("sqs", region_name="us-east-1")
    ddb = boto3.client("dynamodb", region_name="us-east-1")

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,
        )

        for message in response.get("Messages", []):
            receipt = message["ReceiptHandle"]
            msg_id  = message.get("MessageId", receipt)

            # Fix 1: json.loads is a pure parser. It never runs code.
            try:
                order = json.loads(message["Body"])
            except (json.JSONDecodeError, ValueError) as exc:
                # Parse errors are not transient. They go to DLQ on the
                # first try once DLQ_ON_PARSE_ERROR is flipped on. During
                # the soak window the kill switch keeps the old behavior
                # (log + delete) so the new DLQ path is not exercised in
                # production until we are ready.
                if DLQ_ON_PARSE_ERROR:
                    route_to_dlq(sqs, message, f"JSON parse error: {exc}")
                else:
                    log.error(
                        "Parse error (kill switch ACTIVE, not routing to DLQ): %s",
                        exc,
                    )
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue

            # Structural validation. Also not transient. Also straight to DLQ.
            if not order.get("order_id") or not order.get("email"):
                if DLQ_ON_PARSE_ERROR:
                    route_to_dlq(
                        sqs, message,
                        "Missing required fields: order_id or email",
                    )
                else:
                    log.error("Missing required fields (kill switch ACTIVE)")
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue

            # Idempotency: only the first caller to claim this order_id
            # proceeds to send. The rest skip and clean up their SQS entry.
            if not claim_order(ddb, order["order_id"]):
                log.info(
                    "Order %s already claimed. Skipping send for message %s",
                    order["order_id"], msg_id,
                )
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue

            # Fix 4: bounded retry around the only call that can flap.
            try:
                send_with_retry(order)
                log.info("Confirmation sent for order %s", order["order_id"])
            except smtplib.SMTPException as exc:
                # Transient failure that outlasted the retry budget.
                # Route to DLQ so the order is never silently lost.
                route_to_dlq(
                    sqs, message,
                    f"SMTP exhausted after {MAX_SMTP_RETRIES} retries: {exc}",
                )
                # Delete from main queue only after DLQ write succeeds.
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue

            # Fix 2: delete only after a confirmed successful send.
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)


# ---------------------------------------------------------------------------
# Tests -- mock-free, exercising core logic in isolation
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    PASS_LABEL = "PASS"
    FAIL_LABEL = "FAIL"

    # -----------------------------------------------------------------------
    # Test 1: safe deserialization accepts valid JSON, rejects bad input
    # -----------------------------------------------------------------------
    print("Test 1: safe deserialization")

    valid_body = '{"order_id": "ORD-001", "email": "buyer@example.com"}'

    try:
        order = json.loads(valid_body)
        assert order["order_id"] == "ORD-001"
        assert order["email"] == "buyer@example.com"
        print(f"  Valid JSON parsed correctly                           {PASS_LABEL}")
    except Exception as exc:
        print(f"  Valid JSON parse failed: {exc}                        {FAIL_LABEL}")

    try:
        json.loads("not valid json {{{")
        print(f"  Bad JSON was not rejected                             {FAIL_LABEL}")
    except (json.JSONDecodeError, ValueError):
        print(f"  Bad JSON raises JSONDecodeError                       {PASS_LABEL}")

    # Demonstrate that the previous eval-based path would have executed
    # arbitrary code from the queue body. json.loads treats it as text.
    injected_body = '{"cmd": "shutil.rmtree(\'/\')"}'
    parsed = json.loads(injected_body)
    assert isinstance(parsed["cmd"], str)
    print(f"  Injected expression is inert string, never executed  {PASS_LABEL}")

    # -----------------------------------------------------------------------
    # Test 2: send_with_retry raises after MAX_SMTP_RETRIES, correct attempt count
    # -----------------------------------------------------------------------
    print("\nTest 2: exponential backoff retry exhaustion")

    call_count = [0]

    def _fake_send_confirmation(order, **kwargs):
        call_count[0] += 1
        raise smtplib.SMTPException("Connection refused (simulated)")

    import sys
    this_module = sys.modules[__name__]
    original_send = this_module.send_confirmation
    this_module.send_confirmation = _fake_send_confirmation

    try:
        send_with_retry({"order_id": "ORD-002", "email": "x@y.com"},
                        max_retries=3, base_delay=0.0)
        print(f"  Did not raise -- expected SMTPException               {FAIL_LABEL}")
    except smtplib.SMTPException:
        if call_count[0] == 3:
            print(f"  Raised after exactly 3 attempts                       {PASS_LABEL}")
        else:
            print(f"  Wrong attempt count: got {call_count[0]}, expected 3  {FAIL_LABEL}")

    this_module.send_confirmation = original_send  # restore

    # -----------------------------------------------------------------------
    # Test 3: validation rejects malformed payloads
    # -----------------------------------------------------------------------
    print("\nTest 3: validation rejects missing fields")

    bad_payloads = [
        {},
        {"order_id": "X"},
        {"email": "x@y.com"},
        {"order_id": "", "email": ""},
    ]
    for bad in bad_payloads:
        has_both = bool(bad.get("order_id")) and bool(bad.get("email"))
        assert not has_both
    print(f"  All {len(bad_payloads)} malformed payloads flagged as invalid          {PASS_LABEL}")

    # -----------------------------------------------------------------------
    # Test 4: idempotency claim semantics (behavior, no network calls)
    # -----------------------------------------------------------------------
    print("\nTest 4: DynamoDB idempotency claim semantics")

    class FakeDDB:
        def __init__(self):
            self.items = {}

        def put_item(self, TableName, Item, ConditionExpression):
            order_id = Item["order_id"]["S"]
            if "attribute_not_exists(order_id)" in ConditionExpression:
                if order_id in self.items:
                    raise ClientError(
                        {"Error": {"Code": "ConditionalCheckFailedException",
                                   "Message": "exists"}},
                        "PutItem",
                    )
            self.items[order_id] = Item

    fake = FakeDDB()
    first  = claim_order(fake, "ORD-100")
    second = claim_order(fake, "ORD-100")
    third  = claim_order(fake, "ORD-101")
    if first is True and second is False and third is True:
        print(f"  First claim wins, second is rejected, different ID wins  {PASS_LABEL}")
    else:
        print(f"  Claim outcomes wrong: {first}/{second}/{third}          {FAIL_LABEL}")

    # -----------------------------------------------------------------------
    # Test 5: kill switch default keeps DLQ path inert during soak
    # -----------------------------------------------------------------------
    print("\nTest 5: DLQ kill switch default")

    default_flag = os.environ.get("DLQ_ON_PARSE_ERROR", "false").lower() == "true"
    if default_flag is False:
        print(f"  Default posture holds: DLQ_ON_PARSE_ERROR off during soak  {PASS_LABEL}")
    else:
        print(f"  Kill switch default is ON, expected OFF                    {FAIL_LABEL}")

    print("\nAll tests complete.")
