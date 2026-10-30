"""C006 계산 검증 — 상수는 docs/work-plans/2026-10-30-C006-상속주택.md §0 법령 기대값·§2 대조 8항목.

변형(§2): 피상속인 취득일 없는 상속(범위 밖), 피상속인 취득 2024-01-01(세율 보유기간 1년 7개월 → 60%).
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

CASE = ROOT / "cases" / "house" / "C006.yaml"


def load_input(case=CASE):
    return yaml.safe_load(case.read_text(encoding="utf-8"))["input"]


def compute_with(case=CASE, **changes):
    inp = copy.deepcopy(load_input(case))
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC006(unittest.TestCase):
    """§2 대조 8항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_eight_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 47_000_000)
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["income_amount"], 47_000_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 44_500_000)
        self.assertEqual(a["rate"], 15)
        self.assertEqual(a["progressive_deduction"], 1_260_000)
        self.assertEqual(a["tax"], 5_415_000)
        self.assertEqual(a["local_tax"], 541_500)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["necessary_expenses"], 703_000_000)  # 상속개시일 평가액 + 양도비, 개산공제 없음
        self.assertEqual(h["holding_years"], 0)  # 장특 기준: 상속개시일부터(§95④)
        self.assertEqual(h["rate_holding_years"], 20)  # 세율 기준: 피상속인 취득일부터(§104②1)
        self.assertEqual(h["rate_rule"], "basic")
        self.assertEqual(h["surcharge_status"], "not_adjusted")
        self.assertFalse(h["one_house_exempt"])
        self.assertEqual(h["holding_rate_pct"], 0)

    def test_basis_for_every_step(self):
        b = self.res["basis"]
        self.assertEqual(set(b), set(self.amt))
        self.assertIn("§104②1(상속: 피상속인 취득일부터)", b["rate"])
        self.assertIn("§95④·시행령 §162①5(상속개시일부터)", b["holding_deduction"])
        self.assertIn("시행령 §163⑨", b["gain"])


class TestC006Variants(unittest.TestCase):
    """§2 변형."""

    def test_missing_decedent_date_out_of_scope(self):
        with self.assertRaises(NotImplementedError):
            compute_with(decedent_acquisition_date=None)

    def test_decedent_short_holding_60(self):
        # 피상속인 취득 2024-01-01 → 양도 2025-08-20 통산 1년 7개월 → §104①2 주택 60%
        # 44,500,000 × 60% = 26,700,000 > 기본세율 5,415,000
        a, h = compute_with(decedent_acquisition_date=dt.date(2024, 1, 1))
        self.assertEqual(h["rate_holding_years"], 1)
        self.assertEqual(h["rate_rule"], "short_term")
        self.assertEqual(a["rate"], 60)
        self.assertEqual(a["tax"], 26_700_000)

    def test_inherited_one_house_out_of_scope(self):
        with self.assertRaises(NotImplementedError):
            compute_with(one_house=True, house_count=1)


if __name__ == "__main__":
    unittest.main()
