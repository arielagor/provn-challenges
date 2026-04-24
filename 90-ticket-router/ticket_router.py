"""
ticket_router.py

Support ticket router for PROVN Challenge 90.

Reads tickets from a JSON file, assigns a priority (HIGH, MEDIUM, LOW),
routes each ticket to the correct support queue (urgent-queue,
standard-queue, backlog-queue), and prints the processed result.

Usage:
    python ticket_router.py [path/to/tickets.json]
    python ticket_router.py --test

If no path is given, the script falls back to "tickets.json" in the
current working directory.

Priority rules (from spec):
    HIGH    customer_tier == "premium"
            OR subject/description contains any of:
            "urgent", "cannot", "broken", "down", "failed"
    MEDIUM  everything else that still has a non-empty description
    LOW     description field is absent or empty

Routing rules (from spec):
    HIGH   -> urgent-queue
    MEDIUM -> standard-queue
    LOW    -> backlog-queue

Edge cases handled:
    1. description field absent (not just empty string)
    2. customer_tier value the rules do not cover (e.g., "enterprise")
    3. same customer_id within 60 seconds (flagged as possible duplicate
       but still routed; reasoning lives in readme.md Section B)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Spec-defined keywords. Case-insensitive substring match on subject or description.
HIGH_PRIORITY_KEYWORDS = ["urgent", "cannot", "broken", "down", "failed"]

# Spec-defined routing map.
QUEUE_BY_PRIORITY = {
    "HIGH": "urgent-queue",
    "MEDIUM": "standard-queue",
    "LOW": "backlog-queue",
}

# Window for the same-customer duplicate check.
DUPLICATE_WINDOW_SECONDS = 60


def has_keyword_hit(text, keywords):
    """Case-insensitive substring match. Empty or None text returns False."""
    if not text:
        return False
    lowered = text.lower()
    for kw in keywords:
        if kw in lowered:
            return True
    return False


def get_description(ticket):
    """
    Return description string, or empty string if absent.
    Spec calls out that the field may be entirely missing, not just empty.
    """
    value = ticket.get("description")
    if value is None:
        return ""
    return value


def assign_priority(ticket):
    """
    Apply spec priority rules in order.

    Rule ordering matters. Premium tier and keyword hits promote to HIGH
    even if the ticket would otherwise land in LOW (empty description)
    or MEDIUM. This matches the spec wording: HIGH is an OR of two
    conditions, not gated by having a description.
    """
    tier = ticket.get("customer_tier")
    subject = ticket.get("subject", "")
    description = get_description(ticket)

    # Premium promotes to HIGH regardless of other fields.
    if tier == "premium":
        return "HIGH"

    # Keyword hit in subject OR description promotes to HIGH.
    if has_keyword_hit(subject, HIGH_PRIORITY_KEYWORDS):
        return "HIGH"
    if has_keyword_hit(description, HIGH_PRIORITY_KEYWORDS):
        return "HIGH"

    # No description at all (absent or empty) -> LOW.
    if not description.strip():
        return "LOW"

    # Anything remaining with a real description -> MEDIUM.
    # Unknown customer_tier values (e.g. "enterprise", "trial", None)
    # fall through to this branch. Not premium, not HIGH by keyword,
    # but has a description, so MEDIUM.
    return "MEDIUM"


def route_ticket(priority):
    """Look up the queue for a priority. Fall back to backlog if unknown."""
    return QUEUE_BY_PRIORITY.get(priority, "backlog-queue")


def parse_submitted_at(value):
    """Parse an ISO-8601 timestamp. Returns None on failure."""
    if not value:
        return None
    try:
        # Normalize "Z" suffix so fromisoformat parses it on all supported runtimes.
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def flag_possible_duplicates(tickets):
    """
    Mark tickets that share a customer_id with an earlier ticket in the
    list, submitted within DUPLICATE_WINDOW_SECONDS. Flag only; routing
    is not suppressed. Reasoning in readme.md Section B.
    """
    last_seen = {}  # customer_id -> datetime of most recent ticket
    for ticket in tickets:
        cid = ticket.get("customer_id")
        ts = parse_submitted_at(ticket.get("submitted_at"))
        ticket["_possible_duplicate"] = False
        if cid and ts:
            prior = last_seen.get(cid)
            if prior is not None:
                delta = abs((ts - prior).total_seconds())
                if delta <= DUPLICATE_WINDOW_SECONDS:
                    ticket["_possible_duplicate"] = True
            last_seen[cid] = ts
    return tickets


def process_tickets(tickets):
    """
    Run the full pipeline: duplicate flagging, priority, routing.
    Returns a list of result dicts with id, priority, queue, and the
    duplicate flag so downstream callers can decide what to do.
    """
    flag_possible_duplicates(tickets)
    results = []
    for t in tickets:
        priority = assign_priority(t)
        queue = route_ticket(priority)
        results.append({
            "id": t.get("id"),
            "priority": priority,
            "queue": queue,
            "possible_duplicate": t.get("_possible_duplicate", False),
        })
    return results


def load_tickets(path):
    """Read JSON file and return the tickets list."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("tickets", [])


def main(argv):
    if len(argv) > 1:
        path = Path(argv[1])
    else:
        path = Path("tickets.json")

    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        sys.exit(1)

    tickets = load_tickets(path)
    results = process_tickets(tickets)
    print(json.dumps(results, indent=2))


# ===========================================================================
# Embedded tests
# ===========================================================================
# Two test inputs below. Run them with `python ticket_router.py --test`.
# Expected output is shown in the docstring of each test function.

SPEC_SAMPLE_TICKETS = [
    {
        "id": "T-1001",
        "customer_id": "C-4421",
        "customer_tier": "premium",
        "subject": "Cannot log in to account",
        "description": "Unable to access my account for two days. Urgent.",
        "submitted_at": "2026-03-15T09:32:00Z",
    },
    {
        "id": "T-1002",
        "customer_id": "C-8810",
        "customer_tier": "standard",
        "subject": "How do I export a report?",
        "description": "I cannot find the export button on the reports page.",
        "submitted_at": "2026-03-15T09:45:00Z",
    },
    {
        "id": "T-1003",
        "customer_id": "C-2233",
        "customer_tier": "standard",
        "subject": "Billing question",
        "submitted_at": "2026-03-15T10:01:00Z",
    },
]

EDGE_CASE_TICKETS = [
    # Unknown tier "enterprise" with plain subject and description.
    # Expected: MEDIUM -> standard-queue.
    {
        "id": "T-2001",
        "customer_id": "C-9001",
        "customer_tier": "enterprise",
        "subject": "Question about API rate limits",
        "description": "Looking for the documented per-minute limits.",
        "submitted_at": "2026-03-15T11:00:00Z",
    },
    # Same customer_id as T-2001, 30 seconds later. Expected: duplicate flag True.
    # Also MEDIUM -> standard-queue.
    {
        "id": "T-2002",
        "customer_id": "C-9001",
        "customer_tier": "enterprise",
        "subject": "Follow up on rate limit question",
        "description": "Adding a second note. Sorry for the double send.",
        "submitted_at": "2026-03-15T11:00:30Z",
    },
    # No description field at all, unknown tier "trial". Expected: LOW -> backlog-queue.
    {
        "id": "T-2003",
        "customer_id": "C-9002",
        "customer_tier": "trial",
        "subject": "hello",
        "submitted_at": "2026-03-15T11:05:00Z",
    },
    # Description contains "broken" keyword, standard tier. Expected: HIGH -> urgent-queue.
    {
        "id": "T-2004",
        "customer_id": "C-9003",
        "customer_tier": "standard",
        "subject": "Quick note",
        "description": "The upload widget is broken for large files.",
        "submitted_at": "2026-03-15T11:10:00Z",
    },
]


def test_spec_sample():
    """
    Expected-path test using the three sample tickets from the spec.

    Expected output:
        T-1001 -> HIGH  -> urgent-queue   (premium tier AND 'cannot' in subject)
        T-1002 -> HIGH  -> urgent-queue   ('cannot' in description)
        T-1003 -> LOW   -> backlog-queue  (no description field)
    """
    results = process_tickets([dict(t) for t in SPEC_SAMPLE_TICKETS])
    by_id = {r["id"]: r for r in results}

    assert by_id["T-1001"]["priority"] == "HIGH", by_id["T-1001"]
    assert by_id["T-1001"]["queue"] == "urgent-queue", by_id["T-1001"]

    assert by_id["T-1002"]["priority"] == "HIGH", by_id["T-1002"]
    assert by_id["T-1002"]["queue"] == "urgent-queue", by_id["T-1002"]

    assert by_id["T-1003"]["priority"] == "LOW", by_id["T-1003"]
    assert by_id["T-1003"]["queue"] == "backlog-queue", by_id["T-1003"]

    print("test_spec_sample passed")
    for r in results:
        print(" ", r)


def test_edge_cases():
    """
    Edge case test covering all three spec edge cases.

    Expected output:
        T-2001 -> MEDIUM -> standard-queue  (unknown tier 'enterprise', plain text)
        T-2002 -> MEDIUM -> standard-queue  (same customer_id within 30s, duplicate flag)
        T-2003 -> LOW    -> backlog-queue   (no description field, unknown tier 'trial')
        T-2004 -> HIGH   -> urgent-queue    (keyword 'broken' in description)
    """
    results = process_tickets([dict(t) for t in EDGE_CASE_TICKETS])
    by_id = {r["id"]: r for r in results}

    assert by_id["T-2001"]["priority"] == "MEDIUM", by_id["T-2001"]
    assert by_id["T-2001"]["queue"] == "standard-queue", by_id["T-2001"]
    assert by_id["T-2001"]["possible_duplicate"] is False, by_id["T-2001"]

    assert by_id["T-2002"]["priority"] == "MEDIUM", by_id["T-2002"]
    assert by_id["T-2002"]["queue"] == "standard-queue", by_id["T-2002"]
    assert by_id["T-2002"]["possible_duplicate"] is True, by_id["T-2002"]

    assert by_id["T-2003"]["priority"] == "LOW", by_id["T-2003"]
    assert by_id["T-2003"]["queue"] == "backlog-queue", by_id["T-2003"]

    assert by_id["T-2004"]["priority"] == "HIGH", by_id["T-2004"]
    assert by_id["T-2004"]["queue"] == "urgent-queue", by_id["T-2004"]

    print("test_edge_cases passed")
    for r in results:
        print(" ", r)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_spec_sample()
        test_edge_cases()
    else:
        main(sys.argv)
