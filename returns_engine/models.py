"""Domain models for the PS-049 reverse logistics engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

class Reason(str, Enum):
    WRONG_ITEM = "WRONG_ITEM"
    DAMAGED_IN_TRANSIT = "DAMAGED_IN_TRANSIT"
    CHANGED_MIND = "CHANGED_MIND"
    DEFECTIVE = "DEFECTIVE"

class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    ACCEPT_WITH_DEDUCTION = "ACCEPT_WITH_DEDUCTION"

class State(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    PICKED = "PICKED"
    RECEIVED = "RECEIVED"
    GRADED = "GRADED"
    RESTOCKED = "RESTOCKED"
    REFURB_IN_PROGRESS = "REFURB_IN_PROGRESS"
    RESOLD = "RESOLD"
    LIQUIDATED = "LIQUIDATED"
    SCRAPPED = "SCRAPPED"
    REJECTED = "REJECTED"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"

class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

class Route(str, Enum):
    RESTOCK = "RESTOCK"
    REFURB = "REFURB"
    LIQUIDATE = "LIQUIDATE"
    SCRAP = "SCRAP"

@dataclass
class Order:
    order_id: str
    sku: str
    category: str
    price_paid: float
    delivery_at: datetime
    seller_id: str
    policy_window_days: int
    payment_type: str
    serial_number: str
    declared_value: float
    customer_id: str
    category_tags: list[str] = field(default_factory=list)

@dataclass
class ReturnCase:
    case_id: str
    order_id: str
    customer_id: str
    reason: Reason
    requested_at: datetime
    evidence_flags: dict[str, Any] = field(default_factory=dict)
    is_exchange: bool = False
    replacement_sku: str | None = None
    decision: Decision | None = None
    decision_reason: str = ""
    state: State = State.REQUESTED
    state_history: list[dict[str, str]] = field(default_factory=list)
    pickup_attempts: list[dict[str, Any]] = field(default_factory=list)
    reopen_count: int = 0
    score: int | None = None
    grade: Grade | None = None
    route: Route | None = None
    recovery_value: float = 0.0
    refurb_cost: float = 0.0
    disposal_cost: float = 0.0
    qc_passed: bool | None = None
    gross_refund: float = 0.0
    restocking_fee: float = 0.0
    pickup_fee: float = 0.0
    accessory_deduction: float = 0.0
    net_refund: float = 0.0
    refund_approval: str = "NOT_READY"
    refund_initiated_at: datetime | None = None
    expected_settlement: str = ""
    seller_recovery: float = 0.0
    courier_claim: float = 0.0
    platform_loss: float = 0.0
    loss_bearer: str = "UNASSIGNED"
    manager_approved: bool = False
    wallet_adjustment: float = 0.0
    receipt_at: datetime | None = None

    def record_state(self, state: State, at: datetime) -> None:
        self.state = state
        self.state_history.append({"state": state.value, "at": at.isoformat()})
