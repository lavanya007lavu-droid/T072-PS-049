"""Deterministic case-file and weekly summary reporting (BR-41, BR-42)."""
from collections import Counter
from dataclasses import asdict
from enum import Enum
from .models import ReturnCase

def _clean(value):
    if isinstance(value, Enum): return value.value
    if hasattr(value, "isoformat"): return value.isoformat()
    if isinstance(value, dict): return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list): return [_clean(v) for v in value]
    return value

def case_report(case: ReturnCase) -> dict:
    data = asdict(case)
    return _clean(data)

def weekly_report(cases: list[ReturnCase]) -> dict:
    counts = Counter(c.route.value if c.route else "NOT_GRADED" for c in cases)
    return {
        "case_count": len(cases),
        "disposition_counts": {key: counts.get(key, 0) for key in ["RESTOCK", "REFURB", "LIQUIDATE", "SCRAP", "NOT_GRADED"]},
        "total_recovery_value": round(sum(c.recovery_value for c in cases), 2),
        "total_refurbishment_cost": round(sum(c.refurb_cost for c in cases), 2),
        "total_disposal_cost": round(sum(c.disposal_cost for c in cases), 2),
        "total_customer_refunds": round(sum(c.net_refund for c in cases if c.refund_approval == "INITIATED"), 2),
        "pending_manager_refunds": round(sum(c.net_refund for c in cases if c.refund_approval == "PENDING_MANAGER_APPROVAL"), 2),
        "seller_recovery": round(sum(c.seller_recovery for c in cases), 2),
        "courier_claims": round(sum(c.courier_claim for c in cases), 2),
        "platform_loss": round(sum(c.platform_loss for c in cases), 2),
    }
