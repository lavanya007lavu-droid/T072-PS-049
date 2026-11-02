"""Application service implementing the PS-049 return workflow."""
from datetime import timedelta
from .models import ReturnCase, Order, Reason, Decision, State, Grade, Route
from .eligibility import evaluate
from .state_machine import transition
from .grading import calculate_score, grade_for_score, recovery_and_cost
from .refunds import calculate_refund, set_settlement, allocate_loss, apply_exchange_adjustment

class ReturnEngine:
    def __init__(self, orders: dict[str, Order]):
        self.orders = orders
        self.cases: dict[str, ReturnCase] = {}
        self.history: list[dict] = []

    def request_return(self, raw: dict) -> ReturnCase:
        case_id = str(raw["case_id"])
        if case_id in self.cases: raise ValueError(f"Duplicate case_id: {case_id}")
        order_id = str(raw["order_id"])
        if order_id not in self.orders: raise ValueError(f"Unknown order_id: {order_id}")
        order = self.orders[order_id]
        requested_at = self._dt(raw["requested_at"])
        reason = Reason(str(raw["reason"]).upper())
        is_exchange = bool(raw.get("is_exchange", False))
        replacement_sku = raw.get("replacement_sku")
        if is_exchange and replacement_sku != order.sku:
            raise ValueError("Exchange is supported only for the same SKU as the original order")
        case = ReturnCase(case_id, order_id, str(raw.get("customer_id", order.customer_id)), reason,
                          requested_at, dict(raw.get("evidence_flags", {})), is_exchange,
                          replacement_sku)
        case.record_state(State.REQUESTED, requested_at)
        decision, explanation, abuse = evaluate(order, case, self.history)
        case.decision, case.decision_reason = decision, explanation
        if decision == Decision.REJECT:
            transition(case, State.REJECTED, requested_at)
        else:
            transition(case, State.APPROVED, requested_at)
            transition(case, State.PICKUP_SCHEDULED, requested_at)
        self.cases[case_id] = case
        if reason == Reason.CHANGED_MIND:
            self.history.append({"customer_id": case.customer_id, "reason": reason.value, "requested_at": requested_at})
        case.evidence_flags["repeat_return_abuse"] = abuse
        return case

    def pickup_attempt(self, case_id: str, attempted_at: str, outcome: str) -> ReturnCase:
        case = self._case(case_id); at = self._dt(attempted_at); outcome = outcome.upper()
        if case.state != State.PICKUP_SCHEDULED: raise ValueError("Pickup can only be recorded while PICKUP_SCHEDULED")
        if outcome not in {"SUCCESS", "FAILED"}: raise ValueError("Pickup outcome must be SUCCESS or FAILED")
        if len(case.pickup_attempts) >= 2: raise ValueError("Maximum two pickup attempts allowed")
        if case.pickup_attempts:
            expected = case.pickup_attempts[-1]["at"] + timedelta(days=1)
            if at.date() != expected.date(): raise ValueError("Pickup attempts must be on consecutive calendar days")
        case.pickup_attempts.append({"attempt": len(case.pickup_attempts)+1, "at": at, "outcome": outcome})
        if outcome == "SUCCESS":
            transition(case, State.PICKED, at)
            if case.is_exchange: case.evidence_flags["replacement_shipped_at"] = at.isoformat()
        elif len(case.pickup_attempts) == 1:
            case.evidence_flags["next_pickup_date"] = (at + timedelta(days=1)).date().isoformat()
        else:
            transition(case, State.CUSTOMER_UNAVAILABLE, at)
            case.refund_approval = "NO_REFUND_CUSTOMER_UNAVAILABLE"
        return case

    def reopen(self, case_id: str, reopened_at: str) -> ReturnCase:
        case = self._case(case_id); at = self._dt(reopened_at)
        if case.state != State.CUSTOMER_UNAVAILABLE: raise ValueError("Only CUSTOMER_UNAVAILABLE cases can be reopened")
        if case.reopen_count >= 1: raise ValueError("Only one reopening is permitted")
        second = case.pickup_attempts[-1]["at"]
        if not (second <= at <= second + timedelta(days=3)): raise ValueError("Reopen must occur within 3 days of second failed pickup")
        case.reopen_count += 1
        transition(case, State.REQUESTED, at)
        transition(case, State.APPROVED, at)
        transition(case, State.PICKUP_SCHEDULED, at)
        case.evidence_flags.setdefault("previous_pickup_cycles", []).append(case.pickup_attempts.copy())
        case.pickup_attempts = []
        return case

    def receive_and_grade(self, case_id: str, receipt: dict) -> ReturnCase:
        case = self._case(case_id); order = self.orders[case.order_id]
        at = self._dt(receipt["received_at"])
        if case.state != State.PICKED: raise ValueError("Unit must be PICKED before warehouse receipt")
        case.receipt_at = at
        transition(case, State.RECEIVED, at)
        if str(receipt.get("returned_serial", "")) != order.serial_number:
            transition(case, State.FRAUD_REVIEW, at)
            case.refund_approval = "NO_REFUND_FRAUD_REVIEW"
            case.decision_reason += "; serial mismatch, sent to FRAUD_REVIEW"
            return case
        score = calculate_score(receipt)
        grade = grade_for_score(score)
        qc = receipt.get("qc_passed")
        if grade == Grade.B and qc is None:
            raise ValueError("Grade B requires qc_passed true/false in receipt data")
        case.score, case.grade = score, grade
        case.evidence_flags["inspection"] = receipt
        transition(case, State.GRADED, at)
        case.qc_passed = qc if grade == Grade.B else None
        route, recovery, refurb_cost, disposal_cost = recovery_and_cost(grade, order.price_paid, qc)
        case.route, case.recovery_value = route, recovery
        case.refurb_cost, case.disposal_cost = refurb_cost, disposal_cost
        if grade == Grade.A:
            transition(case, State.RESTOCKED, at)
        elif grade == Grade.B:
            transition(case, State.REFURB_IN_PROGRESS, at)
            transition(case, State.RESOLD if qc else State.LIQUIDATED, at)
        elif grade == Grade.C:
            transition(case, State.LIQUIDATED, at)
        else:
            transition(case, State.SCRAPPED, at)
        abuse = bool(case.evidence_flags.get("repeat_return_abuse", False))
        if case.reason == Reason.DEFECTIVE and not receipt.get("defect_confirmed", False):
            case.reason = Reason.CHANGED_MIND
            case.decision_reason += "; no defect confirmed, treated as CHANGED_MIND"
        calculate_refund(order, case, receipt, abuse)
        if case.is_exchange:
            case.net_refund = 0.0
            case.refund_approval = "SKIPPED_EXCHANGE"
            apply_exchange_adjustment(order, case)
        elif grade in {Grade.A, Grade.B}:
            case.refund_approval = "INITIATED"
            case.refund_initiated_at = at
            set_settlement(order, case)
        else:
            case.refund_approval = "PENDING_MANAGER_APPROVAL"
        allocate_loss(order, case)
        return case

    def manager_approve(self, case_id: str, approved_at: str) -> ReturnCase:
        case = self._case(case_id); at = self._dt(approved_at)
        if case.grade not in {Grade.C, Grade.D} or case.refund_approval != "PENDING_MANAGER_APPROVAL":
            raise ValueError("Manager approval applies only to pending grade C/D refunds")
        case.manager_approved = True
        case.refund_approval = "INITIATED"
        case.refund_initiated_at = at
        set_settlement(self.orders[case.order_id], case)
        return case

    def _case(self, case_id: str) -> ReturnCase:
        if case_id not in self.cases: raise ValueError(f"Unknown case_id: {case_id}")
        return self.cases[case_id]

    @staticmethod
    def _dt(value):
        from .validation import parse_datetime
        if isinstance(value, str): return parse_datetime(value)
        return value
