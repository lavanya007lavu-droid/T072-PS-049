"""Refund, settlement and loss calculations (BR-09 to BR-16, BR-29 to BR-40)."""
from datetime import timedelta
from .models import ReturnCase, Order, Reason, Grade

def business_days_after(start, days: int):
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current

def calculate_refund(order: Order, case: ReturnCase, inspection: dict, abuse: bool) -> None:
    gross = order.price_paid
    fee_rate = 0.0
    if case.reason == Reason.CHANGED_MIND:
        fee_rate = 0.20 if abuse else 0.10
        case.pickup_fee = 99.0
    elif abuse and case.reason not in {Reason.DAMAGED_IN_TRANSIT}:
        fee_rate = 0.20
        case.pickup_fee = 99.0
    else:
        case.pickup_fee = 0.0
    case.gross_refund = gross
    case.restocking_fee = max(100.0, gross * fee_rate) if fee_rate else 0.0
    accessory_value = sum(float(v) for v in inspection.get("missing_accessory_values", []))
    # The accessory deduction is capped at 30% of the gross refund.
    case.accessory_deduction = min(max(0.0, accessory_value), gross * 0.30)
    case.net_refund = max(0.0, gross - case.restocking_fee - case.pickup_fee - case.accessory_deduction)

def set_settlement(order: Order, case: ReturnCase) -> None:
    if order.payment_type == "COD":
        case.expected_settlement = "WALLET_INSTANT"
    else:
        case.expected_settlement = "SOURCE_WITHIN_5_BUSINESS_DAYS"

def allocate_loss(order: Order, case: ReturnCase) -> None:
    loss = max(0.0, order.price_paid - case.recovery_value)
    if case.reason == Reason.DAMAGED_IN_TRANSIT:
        case.courier_claim = min(loss, order.declared_value, 5000.0)
        case.loss_bearer = "COURIER"
    elif case.reason in {Reason.DEFECTIVE, Reason.WRONG_ITEM}:
        case.seller_recovery = loss
        case.loss_bearer = "SELLER"
    else:
        case.platform_loss = max(0.0, loss - case.restocking_fee)
        case.loss_bearer = "PLATFORM"

def apply_exchange_adjustment(order: Order, case: ReturnCase) -> None:
    if case.is_exchange and case.grade in {Grade.C, Grade.D}:
        case.wallet_adjustment = order.price_paid - case.recovery_value
