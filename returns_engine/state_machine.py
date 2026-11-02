"""Centralized state transition rules (BR-36, BR-37)."""
from datetime import datetime
from .models import State, ReturnCase

ALLOWED = {
    State.REQUESTED: {State.APPROVED, State.REJECTED, State.FRAUD_REVIEW},
    State.APPROVED: {State.PICKUP_SCHEDULED, State.REJECTED, State.FRAUD_REVIEW},
    State.PICKUP_SCHEDULED: {State.PICKED, State.CUSTOMER_UNAVAILABLE, State.REJECTED, State.FRAUD_REVIEW},
    State.PICKED: {State.RECEIVED, State.REJECTED, State.FRAUD_REVIEW},
    State.RECEIVED: {State.GRADED, State.REJECTED, State.FRAUD_REVIEW},
    State.GRADED: {State.RESTOCKED, State.REFURB_IN_PROGRESS, State.LIQUIDATED, State.SCRAPPED},
    State.REFURB_IN_PROGRESS: {State.RESOLD, State.LIQUIDATED},
    State.CUSTOMER_UNAVAILABLE: {State.REQUESTED},
    State.REJECTED: set(), State.FRAUD_REVIEW: set(), State.RESTOCKED: set(),
    State.RESOLD: set(), State.LIQUIDATED: set(), State.SCRAPPED: set(),
}

def transition(case: ReturnCase, target: State, at: datetime) -> None:
    if target not in ALLOWED[case.state]:
        raise ValueError(f"Illegal state transition: {case.state.value} -> {target.value}")
    case.record_state(target, at)
