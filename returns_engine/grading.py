"""Condition scoring, grade mapping and disposition (BR-17 to BR-28)."""
from .models import Grade, Route

def calculate_score(inspection: dict) -> int:
    scratches = int(inspection.get("scratches", 0))
    if scratches < 0:
        raise ValueError("scratches cannot be negative")
    score = 100 - min(scratches * 10, 30)
    if inspection.get("functional_fault", False): score -= 40
    if inspection.get("box_missing", False): score -= 10
    if inspection.get("seal_broken", False): score -= 15
    if inspection.get("usage_detected", False): score -= 20
    return score

def grade_for_score(score: int) -> Grade:
    if score >= 90: return Grade.A
    if score >= 70: return Grade.B
    if score >= 50: return Grade.C
    return Grade.D

def route_for_grade(grade: Grade) -> Route:
    return {Grade.A: Route.RESTOCK, Grade.B: Route.REFURB, Grade.C: Route.LIQUIDATE, Grade.D: Route.SCRAP}[grade]

def recovery_and_cost(grade: Grade, price: float, qc_passed: bool | None = None) -> tuple[Route, float, float, float]:
    route = route_for_grade(grade)
    if grade == Grade.A: return route, price, 0.0, 0.0
    if grade == Grade.B:
        if qc_passed is False: return Route.LIQUIDATE, price * 0.50, 0.0, 0.0
        return route, price * 0.85, 500.0 + price * 0.05, 0.0
    if grade == Grade.C: return route, price * 0.50, 0.0, 0.0
    return route, 0.0, 0.0, 50.0
