"""C005 계산 검증 — 상수는 docs/work-plans/2026-10-29-C005-주택단기세율.md §0 법령 기대값·§2 대조 8항목.

변형(§2·§0 Fable 검토 반영): 보유 11개월 주택 70%(§104①3), 보유 1년 5개월 토지 40%(§104①2),
2021-05-31 양도(범위 밖), §104① 단서 비교(조정2주택 중과 세액 > 단기세율 세액).
실행: python -m unittest discover -s tools/tests -p "test_*.py"
"""

import copy
import datetime as dt
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from calc import yangdo  # noqa: E402

CASE = ROOT / "cases" / "house" / "C005.yaml"
CASE_C003 = ROOT / "cases" / "house" / "C003.yaml"


def load_input(case=CASE):
    return yaml.safe_load(case.read_text(encoding="utf-8"))["input"]


def compute_with(case=CASE, **changes):
    inp = copy.deepcopy(load_input(case))
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC005(unittest.TestCase):
    """§2 대조 8항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_eight_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 92_000_000)
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["income_amount"], 92_000_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 89_500_000)
        self.assertEqual(a["rate"], 60)
        self.assertEqual(a["progressive_deduction"], 0)
        self.assertEqual(a["tax"], 53_700_000)
        self.assertEqual(a["local_tax"], 5_370_000)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["necessary_expenses"], 508_000_000)
        self.assertEqual(h["holding_years"], 1)
        self.assertEqual(h["rate_rule"], "short_term")
        self.assertFalse(h["one_house_exempt"])  # 보유 2년 미달(시행령 §154①)
        self.assertEqual(h["exempt_gain"], 0)  # 고가주택 안분 적용 안 함
        self.assertEqual(h["holding_rate_pct"], 0)

    def test_basis_for_every_step(self):
        self.assertEqual(set(self.res["basis"]), set(self.amt))
        self.assertIn("§104①2·3·단서", self.res["basis"]["rate"])


class TestC005Variants(unittest.TestCase):
    """§2 변형."""

    def test_house_under_one_year_70(self):
        # 취득 2024-09-20 → 양도 2025-08-20 보유 11개월 → §104①3 주택 70%
        a, h = compute_with(acquisition_date=dt.date(2024, 9, 20), residence_start=dt.date(2024, 9, 20))
        self.assertEqual(h["holding_years"], 0)
        self.assertEqual(h["rate_rule"], "short_term")
        self.assertEqual(a["rate"], 70)
        self.assertEqual(a["tax"], 62_650_000)
        self.assertEqual(a["local_tax"], 6_265_000)

    def test_land_one_to_two_years_40(self):
        # 같은 금액의 토지 보유 1년 5개월 → §104①2 그 밖 40% (기본세율 15,885,000 < 35,800,000)
        a, h = compute_with(kind="토지", house=False)
        self.assertEqual(h["rate_rule"], "short_term")
        self.assertEqual(a["rate"], 40)
        self.assertEqual(a["tax"], 35_800_000)
        self.assertEqual(a["local_tax"], 3_580_000)

    def test_before_2021_06_01_out_of_scope(self):
        with self.assertRaises(NotImplementedError):
            compute_with(transfer_date=dt.date(2021, 5, 31), acquisition_date=dt.date(2020, 3, 15),
                         residence_start=dt.date(2020, 3, 15), residence_end=dt.date(2021, 5, 31))

    def test_proviso_surcharge_larger(self):
        # 조정2주택 유예 종료 뒤(C003 입력) 보유 1년 5개월, 과세표준 15억
        # → 기본 45%+20%p: 1,500,000,000×65% − 65,940,000 = 909,060,000 > 60% 900,000,000
        a, h = compute_with(CASE_C003, acquisition_date=dt.date(2025, 2, 15),
                            transfer_date=dt.date(2026, 7, 20),
                            transfer_contract_date=dt.date(2026, 6, 1),
                            transfer_price=2_002_500_000, acquisition_price=500_000_000, expenses=0)
        self.assertEqual(h["surcharge_status"], "surcharged")
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["tax_base"], 1_500_000_000)
        self.assertEqual(h["rate_rule"], "surcharged")
        self.assertEqual(a["rate"], 65)
        self.assertEqual(a["tax"], 909_060_000)

    def test_multi_asset_short_term_out_of_scope(self):
        inp = copy.deepcopy(load_input())
        inp["assets"].append({
            "id": "L1", "kind": "토지", "transfer_date": dt.date(2025, 9, 1),
            "acquisition_date": dt.date(2015, 1, 1), "transfer_price": 100_000_000,
            "acquisition_price": 50_000_000, "expenses": 0, "depreciation": 0,
            "registered": True, "house": False})
        with self.assertRaisesRegex(NotImplementedError, "비교과세"):
            yangdo.compute(inp)


if __name__ == "__main__":
    unittest.main()
