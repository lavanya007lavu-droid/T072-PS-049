import unittest
from datetime import datetime
from returns_engine.validation import load_order, ValidationError
from returns_engine.engine import ReturnEngine
from returns_engine.models import State, Grade, Route, Decision
from returns_engine.grading import calculate_score, grade_for_score
from returns_engine.state_machine import transition

BASE_ORDER = {"order_id":"O1","sku":"SKU1","category":"ELECTRONICS","price_paid":10000,"delivery_at":"2026-10-01T10:00:00+05:30","seller_id":"S1","policy_window_days":7,"payment_type":"PREPAID","serial_number":"SER1","declared_value":9000,"customer_id":"C1"}

def engine(): return ReturnEngine({"O1": load_order(BASE_ORDER)})

def start_case(e, reason="WRONG_ITEM", date="2026-10-08T23:59:00+05:30", case_id="C1", **extra):
    return e.request_return({"case_id":case_id,"order_id":"O1","customer_id":"C1","reason":reason,"requested_at":date,"evidence_flags":{},**extra})

class ValidationTests(unittest.TestCase):
    def test_missing_order_field_rejected(self):
        with self.assertRaises(ValidationError): load_order({"order_id":"x"})
    def test_invalid_payment_rejected(self):
        raw = dict(BASE_ORDER, payment_type="CHEQUE")
        with self.assertRaises(ValidationError): load_order(raw)

class GradingTests(unittest.TestCase):
    def test_three_scratches_and_broken_seal_is_55_grade_c(self):
        score = calculate_score({"scratches":3,"seal_broken":True})
        self.assertEqual(score, 55); self.assertEqual(grade_for_score(score), Grade.C)
    def test_grade_boundaries(self):
        self.assertEqual(grade_for_score(90), Grade.A)
        self.assertEqual(grade_for_score(89), Grade.B)
        self.assertEqual(grade_for_score(70), Grade.B)
        self.assertEqual(grade_for_score(69), Grade.C)
        self.assertEqual(grade_for_score(50), Grade.C)
        self.assertEqual(grade_for_score(49), Grade.D)
    def test_scratch_penalty_capped_at_30(self):
        self.assertEqual(calculate_score({"scratches":9}), 70)

class WorkflowTests(unittest.TestCase):
    def test_day_seven_2359_is_accepted(self):
        c = start_case(engine())
        self.assertEqual(c.decision, Decision.ACCEPT)
    def test_day_eight_is_rejected(self):
        c = start_case(engine(), date="2026-10-09T00:00:00+05:30")
        self.assertEqual(c.decision, Decision.REJECT)
        self.assertEqual(c.state, State.REJECTED)
    def test_no_return_category_rejected(self):
        raw = dict(BASE_ORDER, category="HYGIENE")
        e = ReturnEngine({"O1": load_order(raw)})
        c = e.request_return({"case_id":"C1","order_id":"O1","reason":"WRONG_ITEM","requested_at":"2026-10-02T10:00:00+05:30"})
        self.assertEqual(c.decision, Decision.REJECT)
    def test_serial_mismatch_fraud_no_refund(self):
        e=engine(); start_case(e)
        e.pickup_attempt("C1","2026-10-09T10:00:00+05:30","SUCCESS")
        c=e.receive_and_grade("C1",{"received_at":"2026-10-10T10:00:00+05:30","returned_serial":"WRONG"})
        self.assertEqual(c.state, State.FRAUD_REVIEW); self.assertEqual(c.net_refund, 0)
    def test_accessory_deduction_cap_30_percent(self):
        e=engine(); start_case(e)
        e.pickup_attempt("C1","2026-10-09T10:00:00+05:30","SUCCESS")
        c=e.receive_and_grade("C1",{"received_at":"2026-10-10T10:00:00+05:30","returned_serial":"SER1","missing_accessory_values":[5000]})
        self.assertEqual(c.accessory_deduction, 3000)
    def test_pickup_second_failure_and_reopen(self):
        e=engine(); start_case(e)
        e.pickup_attempt("C1","2026-10-02T10:00:00+05:30","FAILED")
        e.pickup_attempt("C1","2026-10-03T10:00:00+05:30","FAILED")
        c=e.cases["C1"]; self.assertEqual(c.state, State.CUSTOMER_UNAVAILABLE)
        e.reopen("C1","2026-10-05T10:00:00+05:30")
        self.assertEqual(c.reopen_count, 1); self.assertEqual(c.state, State.PICKUP_SCHEDULED)
    def test_illegal_transition_raises(self):
        e=engine(); c=start_case(e)
        with self.assertRaises(ValueError): transition(c, State.RESOLVED if hasattr(State,"RESOLVED") else State.RESOLD, datetime.fromisoformat("2026-10-02T10:00:00+05:30"))
    def test_grade_c_refund_waits_for_manager(self):
        e=engine(); start_case(e)
        e.pickup_attempt("C1","2026-10-02T10:00:00+05:30","SUCCESS")
        c=e.receive_and_grade("C1",{"received_at":"2026-10-03T10:00:00+05:30","returned_serial":"SER1","scratches":3,"seal_broken":True})
        self.assertEqual(c.grade, Grade.C); self.assertEqual(c.route, Route.LIQUIDATE)
        self.assertEqual(c.refund_approval,"PENDING_MANAGER_APPROVAL")
        e.manager_approve("C1","2026-10-04T10:00:00+05:30")
        self.assertEqual(c.refund_approval,"INITIATED")
    def test_grade_b_qc_failure_liquidates(self):
        e=engine(); start_case(e)
        e.pickup_attempt("C1","2026-10-02T10:00:00+05:30","SUCCESS")
        c=e.receive_and_grade("C1",{"received_at":"2026-10-03T10:00:00+05:30","returned_serial":"SER1","scratches":2,"qc_passed":False})
        self.assertEqual(c.route, Route.LIQUIDATE); self.assertEqual(c.state, State.LIQUIDATED)
    def test_exchange_grade_d_wallet_adjustment(self):
        e=engine(); start_case(e, is_exchange=True, replacement_sku="SKU1")
        e.pickup_attempt("C1","2026-10-02T10:00:00+05:30","SUCCESS")
        c=e.receive_and_grade("C1",{"received_at":"2026-10-03T10:00:00+05:30","returned_serial":"SER1","functional_fault":True,"box_missing":True,"seal_broken":True,"usage_detected":True})
        self.assertEqual(c.grade, Grade.D); self.assertEqual(c.net_refund, 0)
        self.assertEqual(c.wallet_adjustment, 10000)
    def test_defective_without_confirmed_fault_becomes_changed_mind(self):
        e=engine()
        e.request_return({"case_id":"C1","order_id":"O1","reason":"DEFECTIVE","requested_at":"2026-10-05T10:00:00+05:30"})
        e.pickup_attempt("C1","2026-10-06T10:00:00+05:30","SUCCESS")
        c=e.receive_and_grade("C1",{"received_at":"2026-10-07T10:00:00+05:30","returned_serial":"SER1","defect_confirmed":False})
        self.assertEqual(c.reason.value,"CHANGED_MIND")
        self.assertEqual(c.restocking_fee,1000)
        self.assertEqual(c.pickup_fee,99)
    def test_repeat_return_third_at_exact_90_day_boundary(self):
        e=engine()
        for index, day in enumerate(["2026-07-10", "2026-08-01"], start=1):
            e.request_return({"case_id":f"OLD{index}","order_id":"O1","reason":"CHANGED_MIND","requested_at":day+"T10:00:00+05:30"})
        c=e.request_return({"case_id":"THIRD","order_id":"O1","reason":"CHANGED_MIND","requested_at":"2026-10-08T10:00:00+05:30"})
        self.assertTrue(c.evidence_flags["repeat_return_abuse"])
    def test_second_pickup_failure_on_sunday_is_counted(self):
        e=engine(); start_case(e, date="2026-10-02T10:00:00+05:30")
        e.pickup_attempt("C1","2026-10-03T10:00:00+05:30","FAILED")
        e.pickup_attempt("C1","2026-10-04T10:00:00+05:30","FAILED")
        self.assertEqual(e.cases["C1"].state,State.CUSTOMER_UNAVAILABLE)
        self.assertEqual(e.cases["C1"].net_refund,0)
    def test_exchange_rejects_different_sku(self):
        e=engine()
        with self.assertRaises(ValueError):
            e.request_return({"case_id":"C1","order_id":"O1","reason":"WRONG_ITEM","requested_at":"2026-10-02T10:00:00+05:30","is_exchange":True,"replacement_sku":"OTHER"})
    def test_courier_claim_capped_at_5000(self):
        e=engine(); start_case(e, reason="DAMAGED_IN_TRANSIT")
        e.pickup_attempt("C1","2026-10-02T10:00:00+05:30","SUCCESS")
        c=e.receive_and_grade("C1",{"received_at":"2026-10-03T10:00:00+05:30","returned_serial":"SER1","functional_fault":True,"box_missing":True,"seal_broken":True,"usage_detected":True})
        self.assertEqual(c.courier_claim, 5000)

if __name__ == "__main__": unittest.main()
