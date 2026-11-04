"""Official PS-049 command processor for the teacher's sample pack.

This version keeps the public interface used by official_cli.py:
    engine = OfficialEngine(data).process()

It processes the pipe-separated command stream in file order and prepares
case_files, state_log, and weekly_rows for output_writer.py.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from .command_parser import parse_commands
from .dataset import MasterData


D = Decimal
ZERO = D("0.00")
CENT = D("0.01")

ALLOWED = {
    "REQUESTED": {"APPROVED", "REJECTED", "FRAUD_REVIEW"},
    "APPROVED": {"PICKUP_SCHEDULED", "REJECTED", "FRAUD_REVIEW"},
    "PICKUP_SCHEDULED": {
        "PICKED", "CUSTOMER_UNAVAILABLE", "REJECTED", "FRAUD_REVIEW"
    },
    "PICKED": {"RECEIVED", "REJECTED", "FRAUD_REVIEW"},
    "RECEIVED": {"GRADED", "REJECTED", "FRAUD_REVIEW"},
    "GRADED": {
        "RESTOCKED", "REFURB_IN_PROGRESS", "LIQUIDATED", "SCRAPPED"
    },
    "REFURB_IN_PROGRESS": {"RESOLD", "LIQUIDATED"},
    "CUSTOMER_UNAVAILABLE": {"REQUESTED"},
    "REJECTED": set(),
    "FRAUD_REVIEW": set(),
    "RESTOCKED": set(),
    "RESOLD": set(),
    "LIQUIDATED": set(),
    "SCRAPPED": set(),
}


def money(value) -> Decimal:
    """Convert a value to a two-decimal Decimal using financial rounding."""
    return D(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def as_bool(value) -> bool:
    """Read CSV booleans without treating arbitrary non-empty strings as true."""
    text = str(value).strip().lower()
    if text not in {"true", "false", ""}:
        raise ValueError(f"Expected true/false boolean, received {value!r}")
    return text == "true"


def timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def date_text(value) -> str:
    return value.isoformat() if value else ""


def amount_text(value) -> str:
    return f"{money(value):.2f}"


class OfficialEngine:
    def __init__(self, data: MasterData):
        self.data = data
        self.cases = {}
        self.state_log = []
        self.case_files = []
        self.weekly_rows = []
        self.changed_mind_dates = defaultdict(list)

        for customer_id, rows in data.prior_returns_by_customer.items():
            for row in rows:
                if row["reason_code"].upper() == "CHANGED_MIND":
                    self.changed_mind_dates[customer_id].append(
                        date.fromisoformat(row["request_date"])
                    )

    def transition(self, case, target, command, reason=""):
        current = case["state"]
        if target not in ALLOWED[current]:
            raise ValueError(
                f"Illegal state transition: {current} -> {target}"
            )

        case["state"] = target
        self.state_log.append({
            "line_no": command["line_no"],
            "return_id": case["return_id"],
            "from_state": current,
            "to_state": target,
            "status": "OK",
            "reason": reason,
        })

    def record_error(self, command, error):
        args = command["args"]
        return_id = "" if command["command"] == "WEEKLY_REPORT" else (
            args[1] if len(args) > 1 else ""
        )
        case = self.cases.get(return_id)
        self.state_log.append({
            "line_no": command["line_no"],
            "return_id": return_id,
            "from_state": case["state"] if case else "",
            "to_state": "",
            "status": "ERROR",
            "reason": str(error),
        })

    def process(self):
        """Execute all validly parsed commands in their original file order."""
        commands = parse_commands(self.data.commands)
        for command in commands:
            try:
                self.execute(command)
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                self.record_error(command, exc)
        return self

    def execute(self, command):
        operation = command["command"]
        args = command["args"]
        at = command["timestamp"]
        handlers = {
            "RETURN_REQUEST": self.return_request,
            "SCHEDULE_PICKUP": self.schedule_pickup,
            "PICKUP_ATTEMPT": self.pickup_attempt,
            "REOPEN": self.reopen,
            "RECEIVE": self.receive,
            "GRADE": self.grade,
            "APPROVE": self.approve,
            "REFURB_QC": self.refurb_qc,
            "PRINT_CASE": self.print_case,
            "WEEKLY_REPORT": self.weekly_report,
        }
        handlers[operation](command, args, at)

    def return_request(self, command, args, at):
        _, return_id, order_id, reason, request_type, evidence = args

        if return_id in self.cases:
            raise ValueError(f"Duplicate return_id: {return_id}")
        if order_id not in self.data.orders:
            raise ValueError(f"Unknown order_id: {order_id}")
        if request_type not in {"REFUND", "EXCHANGE"}:
            raise ValueError(f"Invalid request type: {request_type}")
        if reason not in {
            "WRONG_ITEM", "DAMAGED_IN_TRANSIT", "CHANGED_MIND", "DEFECTIVE"
        }:
            raise ValueError(f"Invalid reason code: {reason}")

        order = self.data.orders[order_id]
        product = self.data.products[order["sku"]]
        category = self.data.categories[product["category"]]

        case = {
            "return_id": return_id,
            "order_id": order_id,
            "customer_id": order["customer_id"],
            "sku": order["sku"],
            "requested_at": at,
            "reason": reason,
            "request_type": request_type,
            "evidence_provided": as_bool(evidence),
            "decision": "",
            "decision_reason": "",
            "state": "REQUESTED",
            "attempts": [],
            "scheduled_date": None,
            "reopen_count": 0,
            "abuse": False,
            "receipt": None,
            "receipt_at": None,
            "grade_record": None,
            "graded_at": None,
            "score": "",
            "grade": "",
            "routing": "",
            "refund_amount": ZERO,
            "restocking_fee": ZERO,
            "pickup_fee": ZERO,
            "accessory_deduction": ZERO,
            "refund_mode": "",
            "refund_date": "",
            "recovery_amount": ZERO,
            "refurb_cost": ZERO,
            "disposal_cost": ZERO,
            "loss_amount": ZERO,
            "loss_bearer": "",
            "courier_claim": ZERO,
            "seller_recovery": ZERO,
            "platform_loss": ZERO,
            "wallet_charge": ZERO,
            "refund_approval": "NOT_READY",
            "refund_initiated_at": None,
            "manager_id": "",
            "replacement_shipped": False,
        }
        self.cases[return_id] = case

        delivered_date = timestamp(order["delivered_ts"]).date()
        elapsed_days = (at.date() - delivered_date).days

        if category["category_class"] == "NO_RETURN":
            decision = "REJECT"
            explanation = "NON_RETURNABLE_CATEGORY"
        else:
            window_key = (
                "doa_window_days" if reason == "DEFECTIVE"
                else "return_window_days"
            )
            window = int(category[window_key])

            # Delivery day is day 0; the complete final calendar day is eligible.
            if elapsed_days < 0 or elapsed_days > window:
                decision = "REJECT"
                explanation = "OUTSIDE_RETURN_WINDOW"
            elif reason == "DEFECTIVE" and not as_bool(evidence):
                decision = "REJECT"
                explanation = "DEFECTIVE_EVIDENCE_MISSING"
            else:
                history = self.changed_mind_dates[case["customer_id"]]
                window_start = at.date() - timedelta(days=90)
                previous_count = sum(
                    1 for item_date in history
                    if window_start <= item_date <= at.date()
                )
                if reason == "CHANGED_MIND":
                    previous_count += 1
                    history.append(at.date())

                case["abuse"] = previous_count >= 3
                receives_deduction = (
                    reason == "CHANGED_MIND"
                    or (case["abuse"] and reason != "DAMAGED_IN_TRANSIT")
                )
                decision = (
                    "ACCEPT_WITH_DEDUCTION" if receives_deduction else "ACCEPT"
                )
                explanation = "RETURN_ACCEPTED"

        case["decision"] = decision
        case["decision_reason"] = explanation
        if decision == "REJECT":
            self.transition(case, "REJECTED", command, explanation)
        else:
            self.transition(case, "APPROVED", command, explanation)

    def schedule_pickup(self, command, args, at):
        _, return_id, pickup_date = args
        case = self.get_case(return_id)
        if case["state"] != "APPROVED":
            raise ValueError("Pickup can only be scheduled for APPROVED cases")

        scheduled = date.fromisoformat(pickup_date)
        if scheduled < at.date():
            raise ValueError("Pickup date cannot be before the scheduling date")
        case["scheduled_date"] = scheduled
        self.transition(case, "PICKUP_SCHEDULED", command, "PICKUP_SCHEDULED")

    def pickup_attempt(self, command, args, at):
        _, return_id, attempt_text, result = args
        case = self.get_case(return_id)
        if case["state"] != "PICKUP_SCHEDULED":
            raise ValueError("Pickup requires PICKUP_SCHEDULED state")

        attempt = int(attempt_text)
        if attempt != len(case["attempts"]) + 1:
            raise ValueError("Pickup attempts must be numbered consecutively")
        if attempt > 2:
            raise ValueError("Maximum two pickup attempts allowed")
        if case["scheduled_date"] is None:
            raise ValueError("Pickup date has not been scheduled")

        expected_date = case["scheduled_date"] + timedelta(days=attempt - 1)
        if at.date() != expected_date:
            raise ValueError(
                "Pickup attempts must occur on the scheduled day and the next day"
            )
        if result not in {"SUCCESS", "FAILED"}:
            raise ValueError("Invalid pickup result")

        case["attempts"].append({
            "attempt": attempt,
            "at": at,
            "result": result,
        })

        if result == "SUCCESS":
            case["replacement_shipped"] = case["request_type"] == "EXCHANGE"
            self.transition(case, "PICKED", command, "PICKUP_SUCCESS")
        elif attempt == 2:
            self.transition(
                case, "CUSTOMER_UNAVAILABLE", command, "SECOND_PICKUP_FAILED"
            )
            case["refund_approval"] = "NO_REFUND_CUSTOMER_UNAVAILABLE"

    def reopen(self, command, args, at):
        _, return_id = args
        case = self.get_case(return_id)
        if case["state"] != "CUSTOMER_UNAVAILABLE":
            raise ValueError("Only CUSTOMER_UNAVAILABLE cases can reopen")
        if case["reopen_count"] >= 1:
            raise ValueError("Only one reopening is allowed")
        if not case["attempts"] or case["attempts"][-1]["result"] != "FAILED":
            raise ValueError("Reopen requires a second failed pickup attempt")

        second_failure = case["attempts"][-1]["at"]
        if not second_failure <= at <= second_failure + timedelta(days=3):
            raise ValueError("Reopening must occur within 3 days of second failed pickup")

        case["reopen_count"] += 1
        case["attempts"] = []
        case["scheduled_date"] = None
        self.transition(case, "REQUESTED", command, "CUSTOMER_REOPENED")
        self.transition(case, "APPROVED", command, "REOPEN_APPROVED")

    def receive(self, command, args, at):
        _, return_id = args
        case = self.get_case(return_id)
        if case["state"] != "PICKED":
            raise ValueError("Unit must be PICKED before RECEIVE")

        receipt = self.data.receipts_by_return.get(return_id)
        if receipt is None:
            raise ValueError("Warehouse receipt record not found")
        if timestamp(receipt["received_ts"]) != at:
            raise ValueError("Receipt timestamp does not match RECEIVE command")

        # Save the receipt timestamp: A/B settlement is initiated from receipt,
        # even though the grade is known only when the later GRADE command runs.
        case["receipt"] = receipt
        case["receipt_at"] = at
        self.transition(case, "RECEIVED", command, "WAREHOUSE_RECEIVED")

        order = self.data.orders[case["order_id"]]
        if receipt["serial_scanned"] != order["serial_number"]:
            self.transition(case, "FRAUD_REVIEW", command, "SERIAL_MISMATCH")
            case["refund_approval"] = "NO_REFUND_FRAUD_REVIEW"

    def grade(self, command, args, at):
        _, return_id = args
        case = self.get_case(return_id)
        if case["state"] != "RECEIVED":
            raise ValueError("GRADE requires RECEIVED state")

        record = self.data.grading_by_return.get(return_id)
        if record is None:
            raise ValueError("Grading record not found")
        if timestamp(record["graded_ts"]) != at:
            raise ValueError("Grading timestamp does not match GRADE command")
        if case["receipt"] is None or case["receipt_at"] is None:
            raise ValueError("GRADE requires a completed warehouse receipt")

        scratches = int(record["cosmetic_scratches"])
        if scratches < 0:
            raise ValueError("Cosmetic scratch count cannot be negative")

        score = 100 - min(scratches * 10, 30)
        if as_bool(record["functional_fault"]):
            score -= 40
        if as_bool(record["original_box_missing"]):
            score -= 10
        if as_bool(record["seal_broken"]):
            score -= 15
        if as_bool(record["usage_detected"]):
            score -= 20

        grade = "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "D"
        case["grade_record"] = record
        case["graded_at"] = at
        case["score"] = score
        case["grade"] = grade
        self.transition(case, "GRADED", command, "UNIT_GRADED")

        # A DEFECTIVE claim without a confirmed warehouse fault is treated as
        # CHANGED_MIND for refund and loss allocation.
        if case["reason"] == "DEFECTIVE" and not as_bool(
            case["receipt"].get("defect_confirmed", "")
        ):
            case["reason"] = "CHANGED_MIND"
            case["decision_reason"] += "; DEFECT_NOT_CONFIRMED"

        order = self.data.orders[case["order_id"]]
        price = money(order["price_paid"])

        if grade == "A":
            case["routing"] = "RESTOCK"
            case["recovery_amount"] = price
            self.transition(case, "RESTOCKED", command, "GRADE_A_RESTOCK")
        elif grade == "B":
            case["routing"] = "REFURB"
            case["recovery_amount"] = money(price * D("0.85"))
            case["refurb_cost"] = money(D("500.00") + price * D("0.05"))
            self.transition(case, "REFURB_IN_PROGRESS", command, "GRADE_B_REFURB")
        elif grade == "C":
            case["routing"] = "LIQUIDATE"
            case["recovery_amount"] = money(price * D("0.50"))
            self.transition(case, "LIQUIDATED", command, "GRADE_C_LIQUIDATE")
        else:
            case["routing"] = "SCRAP"
            case["recovery_amount"] = ZERO
            case["disposal_cost"] = money("50.00")
            self.transition(case, "SCRAPPED", command, "GRADE_D_SCRAP")

        self.calculate_refund(case)

        if case["request_type"] == "EXCHANGE":
            # Exchange ships a replacement on successful pickup and does not
            # initiate a normal refund. Grade C/D charges full price less recovery.
            case["refund_amount"] = ZERO
            case["refund_mode"] = ""
            case["refund_date"] = ""
            case["refund_approval"] = "SKIPPED_EXCHANGE"
            if grade in {"C", "D"}:
                case["wallet_charge"] = money(price - case["recovery_amount"])
                customer = self.data.customers[case["customer_id"]]
                customer["wallet_balance"] = amount_text(
                    money(customer["wallet_balance"]) - case["wallet_charge"]
                )
        elif grade in {"A", "B"}:
            case["refund_approval"] = "INITIATED"
            # The teacher specifies that A/B refunds are initiated on receipt.
            self.initiate_refund(case, case["receipt_at"])
        else:
            case["refund_approval"] = "PENDING_MANAGER_APPROVAL"

        self.calculate_loss(case)

    def calculate_refund(self, case):
        order = self.data.orders[case["order_id"]]
        gross = money(order["price_paid"])

        if case["reason"] == "CHANGED_MIND":
            fee_rate = D("0.20") if case["abuse"] else D("0.10")
            case["pickup_fee"] = money("99.00")
        elif case["abuse"] and case["reason"] != "DAMAGED_IN_TRANSIT":
            fee_rate = D("0.20")
            case["pickup_fee"] = money("99.00")
        else:
            fee_rate = ZERO
            case["pickup_fee"] = ZERO

        case["restocking_fee"] = (
            min(gross, max(money("100.00"), money(gross * fee_rate)))
            if fee_rate else ZERO
        )

        missing_text = case["receipt"].get("accessories_missing", "")
        missing_ids = [item.strip() for item in missing_text.split(";") if item.strip()]
        accessory_rows = self.data.accessories_by_sku.get(case["sku"], [])
        prices_by_id = {
            row["accessory_id"]: money(row["master_price"])
            for row in accessory_rows
        }

        unknown_ids = [item for item in missing_ids if item not in prices_by_id]
        if unknown_ids:
            raise ValueError(
                f"Unknown missing accessory ID(s) for {case['sku']}: {unknown_ids}"
            )

        missing_value = sum((prices_by_id[item] for item in missing_ids), ZERO)
        case["accessory_deduction"] = min(missing_value, money(gross * D("0.30")))
        case["refund_amount"] = max(
            ZERO,
            gross
            - case["restocking_fee"]
            - case["pickup_fee"]
            - case["accessory_deduction"],
        )

        has_deduction = any((
            case["restocking_fee"] > ZERO,
            case["pickup_fee"] > ZERO,
            case["accessory_deduction"] > ZERO,
        ))
        if has_deduction:
            case["decision"] = "ACCEPT_WITH_DEDUCTION"

    def initiate_refund(self, case, initiated_at):
        order = self.data.orders[case["order_id"]]
        case["refund_initiated_at"] = initiated_at

        if order["payment_mode"] == "COD":
            case["refund_mode"] = "WALLET"
            case["refund_date"] = initiated_at.date()
            customer = self.data.customers[case["customer_id"]]
            customer["wallet_balance"] = amount_text(
                money(customer["wallet_balance"]) + case["refund_amount"]
            )
            return

        case["refund_mode"] = "SOURCE"
        settlement_date = initiated_at.date()
        added_business_days = 0
        while added_business_days < 5:
            settlement_date += timedelta(days=1)
            if (
                settlement_date.weekday() < 5
                and settlement_date not in self.data.holidays
            ):
                added_business_days += 1
        case["refund_date"] = settlement_date

    def calculate_loss(self, case):
        """Calculate total economic loss, including refurbishment/disposal cost."""
        order = self.data.orders[case["order_id"]]
        price = money(order["price_paid"])
        total_cost = price + case["refurb_cost"] + case["disposal_cost"]
        loss = max(ZERO, total_cost - case["recovery_amount"])
        case["loss_amount"] = money(loss)

        case["courier_claim"] = ZERO
        case["seller_recovery"] = ZERO
        case["platform_loss"] = ZERO
        case["loss_bearer"] = ""
        if loss == ZERO:
            return

        if case["reason"] == "DAMAGED_IN_TRANSIT":
            # The supplied orders.csv has no declared_value column. Until the
            # coordinator confirms the intended basis, price_paid is used as
            # the available declared-value proxy. The Rs 5,000 cap is applied.
            declared_value = money(order.get("declared_value", order["price_paid"]))
            case["courier_claim"] = min(loss, declared_value, money("5000.00"))
            case["platform_loss"] = max(ZERO, loss - case["courier_claim"])
            case["loss_bearer"] = "COURIER"
        elif case["reason"] in {"DEFECTIVE", "WRONG_ITEM"}:
            case["seller_recovery"] = loss
            case["loss_bearer"] = "SELLER"
        else:
            case["platform_loss"] = max(
                ZERO, loss - case["restocking_fee"]
            )
            case["loss_bearer"] = "PLATFORM"

    def approve(self, command, args, at):
        _, return_id, manager_id = args
        case = self.get_case(return_id)
        if case["request_type"] == "EXCHANGE":
            raise ValueError("Manager refund approval is not applicable to exchanges")
        if case["grade"] not in {"C", "D"}:
            raise ValueError("APPROVE applies only to grade C/D")
        if case["refund_approval"] != "PENDING_MANAGER_APPROVAL":
            raise ValueError("Refund is not pending manager approval")

        case["manager_id"] = manager_id
        case["refund_approval"] = "INITIATED"
        self.initiate_refund(case, at)

    def refurb_qc(self, command, args, at):
        _, return_id, result = args
        case = self.get_case(return_id)
        if case["state"] != "REFURB_IN_PROGRESS":
            raise ValueError("REFURB_QC requires REFURB_IN_PROGRESS")

        order = self.data.orders[case["order_id"]]
        price = money(order["price_paid"])
        if result == "PASS":
            case["routing"] = "REFURB"
            case["recovery_amount"] = money(price * D("0.85"))
            self.transition(case, "RESOLD", command, "REFURB_QC_PASS")
        elif result == "FAIL":
            case["routing"] = "LIQUIDATE"
            case["recovery_amount"] = money(price * D("0.50"))
            self.transition(case, "LIQUIDATED", command, "REFURB_QC_FAIL")
        else:
            raise ValueError("REFURB_QC result must be PASS or FAIL")

        # Refurbishment cost is retained on both PASS and FAIL because the
        # refurbishment work was incurred before the QC result.
        self.calculate_loss(case)

    def print_case(self, command, args, at):
        _, return_id = args
        case = self.get_case(return_id)
        self.case_files.append({
            "return_id": case["return_id"],
            "order_id": case["order_id"],
            "decision": case["decision"],
            "final_state": case["state"],
            "grade": case["grade"],
            "score": case["score"],
            "routing": case["routing"],
            "refund_amount": amount_text(case["refund_amount"]),
            "restocking_fee": amount_text(case["restocking_fee"]),
            "pickup_fee": amount_text(case["pickup_fee"]),
            "accessory_deduction": amount_text(case["accessory_deduction"]),
            "refund_mode": case["refund_mode"],
            "refund_date": date_text(case["refund_date"]),
            "recovery_amount": amount_text(case["recovery_amount"]),
            "loss_amount": amount_text(case["loss_amount"]),
            "loss_bearer": case["loss_bearer"],
            "courier_claim": amount_text(case["courier_claim"]),
            "wallet_charge": amount_text(case["wallet_charge"]),
        })

    def weekly_report(self, command, args, at):
        _, start_text, end_text = args
        start = date.fromisoformat(start_text)
        end = date.fromisoformat(end_text)
        if start > end:
            raise ValueError("week_start cannot be after week_end")

        selected = [
            case for case in self.cases.values()
            if case["graded_at"] is not None
            and start <= case["graded_at"].date() <= end
        ]

        # Emit one row per routing for every WEEKLY_REPORT command, including
        # zero-unit routes, as required by the output specification.
        for route in ("RESTOCK", "REFURB", "LIQUIDATE", "SCRAP"):
            group = [case for case in selected if case["routing"] == route]
            self.weekly_rows.append({
                "week_start": start_text,
                "week_end": end_text,
                "routing": route,
                "units": len(group),
                "price_total": amount_text(sum((
                    money(self.data.orders[case["order_id"]]["price_paid"])
                    for case in group
                ), ZERO)),
                "recovery_total": amount_text(sum((
                    case["recovery_amount"] for case in group
                ), ZERO)),
                "loss_total": amount_text(sum((
                    case["loss_amount"] for case in group
                ), ZERO)),
                "courier_claims": amount_text(sum((
                    case["courier_claim"] for case in group
                ), ZERO)),
                "seller_recovery": amount_text(sum((
                    case["seller_recovery"] for case in group
                ), ZERO)),
                "platform_loss": amount_text(sum((
                    case["platform_loss"] for case in group
                ), ZERO)),
            })

    def get_case(self, return_id):
        if return_id not in self.cases:
            raise ValueError(f"Unknown return_id: {return_id}")
        return self.cases[return_id]
