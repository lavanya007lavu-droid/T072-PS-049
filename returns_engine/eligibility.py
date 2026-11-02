"""Eligibility and reason-specific fees (BR-02 to BR-11, BR-38)."""
from datetime import timedelta
from .models import Order, ReturnCase, Reason, Decision

NO_RETURN = {"NO_RETURN", "HYGIENE", "SOFTWARE"}

def changed_mind_count(history: list[dict], customer_id: str, requested_at) -> int:
    start = requested_at - timedelta(days=90)
    return sum(1 for item in history if item.get("customer_id") == customer_id
               and item.get("reason") == Reason.CHANGED_MIND.value
               and start <= item.get("requested_at") <= requested_at)

def evaluate(order: Order, case: ReturnCase, history: list[dict]) -> tuple[Decision, str, bool]:
    if order.category in NO_RETURN or "NO_RETURN" in order.category_tags:
        return Decision.REJECT, "Category is non-returnable (NO_RETURN)", False
    if case.reason == Reason.DEFECTIVE:
        window = 30
    elif order.category == "ELECTRONICS":
        window = 7
    elif order.category == "ACCESSORIES":
        window = 15
    else:
        window = order.policy_window_days
    # Inclusive calendar-day boundary: the complete final day is eligible.
    deadline = (order.delivery_at + timedelta(days=window)).replace(hour=23, minute=59, second=59, microsecond=999999)
    if case.requested_at > deadline:
        return Decision.REJECT, f"Return requested outside {window}-day eligibility window", False
    if case.reason == Reason.DEFECTIVE and not case.evidence_flags.get("doa_claim", True):
        return Decision.REJECT, "DEFECTIVE request is missing DOA claim evidence", False
    prior_count = changed_mind_count(history, case.customer_id, case.requested_at)
    # The current CHANGED_MIND request is included in the 3-return threshold.
    abuse = (prior_count + (1 if case.reason == Reason.CHANGED_MIND else 0)) >= 3
    if case.reason in {Reason.WRONG_ITEM, Reason.DAMAGED_IN_TRANSIT}:
        return Decision.ACCEPT, "Eligible reason; full refund subject to receipt checks", abuse
    if case.reason == Reason.DEFECTIVE:
        return Decision.ACCEPT, "Eligible DOA claim; warehouse confirmation required", abuse
    return Decision.ACCEPT_WITH_DEDUCTION, "Changed-mind return; fees apply", abuse
