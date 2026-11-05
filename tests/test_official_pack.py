
import unittest
from pathlib import Path
from decimal import Decimal

from returns_engine.dataset import load_master_data
from returns_engine.command_parser import parse_commands
from returns_engine.official_engine import OfficialEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FOLDER = PROJECT_ROOT / "sample_data" / "teacher_pack"


class OfficialPackTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = load_master_data(str(DATA_FOLDER))
        cls.commands = parse_commands(cls.data.commands)
        cls.engine = OfficialEngine(cls.data).process()

    def test_all_401_commands_are_parsed(self):
        self.assertEqual(len(self.commands), 401)

    def test_all_60_return_cases_are_processed(self):
        self.assertEqual(len(self.engine.cases), 60)

    def test_all_60_case_files_are_generated(self):
        self.assertEqual(len(self.engine.case_files), 60)

    def test_eight_weekly_report_rows_are_generated(self):
        self.assertEqual(len(self.engine.weekly_rows), 8)

    def test_three_scratches_and_broken_seal(self):
        case = self.engine.get_case("RR-0015")
        self.assertEqual(case["score"], 55)
        self.assertEqual(case["grade"], "C")

    def test_grade_b_boundary(self):
        case = self.engine.get_case("RR-0019")
        self.assertEqual(case["score"], 70)
        self.assertEqual(case["grade"], "B")

    def test_courier_claim_cap(self):
        case = self.engine.get_case("RR-0007")
        self.assertEqual(case["courier_claim"], Decimal("5000.00"))

    def test_missing_accessory_deduction_cap(self):
        case = self.engine.get_case("RR-0025")
        self.assertEqual(
            case["accessory_deduction"],
            Decimal("1049.70")
        )

    def test_exchange_grade_d_wallet_charge(self):
        case = self.engine.get_case("RR-0020")
        self.assertEqual(case["grade"], "D")
        self.assertEqual(case["wallet_charge"], Decimal("24999.00"))
        self.assertEqual(case["refund_amount"], Decimal("0.00"))

    def test_refurb_qc_failure(self):
        case = self.engine.get_case("RR-0030")
        self.assertEqual(case["state"], "LIQUIDATED")
        self.assertEqual(case["routing"], "LIQUIDATE")

    def test_second_pickup_failure(self):
        case = self.engine.get_case("RR-0037")
        self.assertEqual(case["state"], "CUSTOMER_UNAVAILABLE")
        self.assertEqual(case["refund_amount"], Decimal("0.00"))

    def test_repeat_return_abuse(self):
        case = self.engine.get_case("RR-0045")
        self.assertTrue(case["abuse"])
        self.assertEqual(case["restocking_fee"], Decimal("799.80"))
        self.assertEqual(case["pickup_fee"], Decimal("99.00"))

    def test_minimum_restocking_fee(self):
        case = self.engine.get_case("RR-0053")
        self.assertEqual(case["restocking_fee"], Decimal("100.00"))
        self.assertEqual(case["pickup_fee"], Decimal("99.00"))

    def test_six_invalid_commands_are_logged(self):
        errors = [
            row for row in self.engine.state_log
            if row["status"] == "ERROR"
        ]

        self.assertEqual(len(errors), 6)

        self.assertEqual(
            {row["line_no"] for row in errors},
            {79, 121, 151, 152, 244, 304}
        )


if __name__ == "__main__":
    unittest.main()
