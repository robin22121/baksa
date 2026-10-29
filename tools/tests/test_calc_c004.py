"""C004 계산 검증 — 상수는 docs/work-plans/2026-10-29-C004-환산취득가액.md §0 법령 기대값·§2 대조 8항목.

변형(§2): 양도비가 환산취득가액 + 개산공제보다 큰 경우(§97②2 단서 → actual_expenses),
기준시가 비율이 정수가 아닌 경우 절사(가정 — 조문 없음, 미실측), 취득가액 불명 + 취득세 입력(범위 밖).
실행: python -m unittest discover -s tools/tests -p "test_*.py"
"""

import copy
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from calc import yangdo  # noqa: E402

CASE = ROOT / "cases" / "house" / "C004.yaml"


def load_input():
    return yaml.safe_load(CASE.read_text(encoding="utf-8"))["input"]


def compute_with(**changes):
    inp = copy.deepcopy(load_input())
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC004(unittest.TestCase):
    """§2 대조 8항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_eight_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 391_600_000)
        self.assertEqual(a["holding_deduction"], 117_480_000)
        self.assertEqual(a["income_amount"], 274_120_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 271_620_000)
        self.assertEqual(a["rate"], 38)
        self.assertEqual(a["progressive_deduction"], 19_940_000)
        self.assertEqual(a["tax"], 83_275_600)
        self.assertEqual(a["local_tax"], 8_327_560)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["converted_acquisition_price"], 400_000_000)
        self.assertEqual(h["estimated_expense"], 8_400_000)
        self.assertEqual(h["necessary_expenses"], 408_400_000)  # 양도비 3,000,000 미포함
        self.assertEqual(h["expense_rule"], "converted")
        self.assertEqual(h["surcharge_status"], "not_adjusted")
        self.assertEqual(h["holding_years"], 15)
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(h["holding_rate_pct"], 30)

    def test_basis_for_every_step(self):
        self.assertEqual(set(self.res["basis"]), set(self.amt))
        self.assertIn("§176의2②2", self.res["basis"]["gain"])


class TestC004Variants(unittest.TestCase):
    """§2 변형."""

    def test_actual_expenses_larger(self):
        # 양도비 500,000,000 > 환산 400,000,000 + 개산 8,400,000 → §97②2 단서
        a, h = compute_with(expenses={"transfer_brokerage": 500_000_000})
        self.assertEqual(h["expense_rule"], "actual_expenses")
        self.assertEqual(h["necessary_expenses"], 500_000_000)
        self.assertEqual(h["converted_acquisition_price"], 400_000_000)
        self.assertEqual(a["gain"], 300_000_000)

    def test_non_integer_ratio_truncated(self):
        # 가정 — 조문 없음, 미실측: 원 미만 절사(floor)
        # 800,000,000 × 280,000,001 ÷ 560,000,000 = 400,000,001.428... → 400,000,001
        # 개산공제 280,000,001 × 3 ÷ 100 = 8,400,000.03 → 8,400,000
        _, h = compute_with(acquisition_std_price=280_000_001)
        self.assertEqual(h["converted_acquisition_price"], 400_000_001)
        self.assertEqual(h["estimated_expense"], 8_400_000)
        self.assertEqual(h["necessary_expenses"], 408_400_001)

    def test_acquisition_tax_with_unknown_out_of_scope(self):
        with self.assertRaisesRegex(NotImplementedError, "acquisition_tax"):
            compute_with(expenses={"acquisition_tax": 5_000_000, "transfer_brokerage": 3_000_000})


if __name__ == "__main__":
    unittest.main()
