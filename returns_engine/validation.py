"""Input parsing and validation (BR-01, BR-43)."""
from datetime import datetime
from .models import Order, Reason

class ValidationError(ValueError):
    pass

def parse_datetime(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Invalid ISO-8601 datetime: {value!r}") from exc
    if result.tzinfo is None:
        raise ValidationError("Datetime must include a timezone offset, for example +05:30 or Z")
    return result

def load_order(raw: dict) -> Order:
    required = ["order_id", "sku", "category", "price_paid", "delivery_at", "seller_id", "policy_window_days", "payment_type", "serial_number", "declared_value", "customer_id"]
    missing = [key for key in required if key not in raw or raw[key] in (None, "")]
    if missing:
        raise ValidationError(f"Order missing required fields: {', '.join(missing)}")
    try:
        price = float(raw["price_paid"]); declared = float(raw["declared_value"]); window = int(raw["policy_window_days"])
    except (TypeError, ValueError) as exc:
        raise ValidationError("price_paid, declared_value and policy_window_days must be numeric") from exc
    if price < 0 or declared < 0 or window < 0:
        raise ValidationError("Prices, declared value and policy window cannot be negative")
    payment = str(raw["payment_type"]).upper()
    if payment not in {"PREPAID", "COD"}:
        raise ValidationError("payment_type must be PREPAID or COD")
    return Order(str(raw["order_id"]), str(raw["sku"]), str(raw["category"]).upper(), price,
                 parse_datetime(raw["delivery_at"]), str(raw["seller_id"]), window, payment,
                 str(raw["serial_number"]), declared, str(raw["customer_id"]),
                 [str(tag).upper() for tag in raw.get("category_tags", [])])

def parse_reason(value: str) -> Reason:
    try:
        return Reason(str(value).upper())
    except ValueError as exc:
        raise ValidationError(f"Unknown reason code: {value}") from exc
