"""C009 계산 검증 — 상수는 docs/work-plans/2026-10-30-C009-비사업용토지.md §0 법령 기대값·§2 대조 8항목.

변형(§2·§4): 보유 1년 6개월 비사업용토지 §104① 단서 비교(과세표준 2억 → 단기 40%, 3억 → 기본+10%p),
사업용 토지(플래그 false) 기본세율, 토지 외 비사업용 플래그(범위 밖).
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

CASE = ROOT / "cases" / "land" / "C009.yaml"


def load_input(case=CASE):
    return yaml.safe_load(case.read_text(encoding="utf-8"))["input"]


def compute_with(case=CASE, **changes):
    inp = copy.deepcopy(load_input(case))
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC009(unittest.TestCase):
    """§2 대조 8항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.t1 = cls.res["assets"][0]

    def test_eight_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 392_000_000)
        self.assertEqual(a["holding_deduction"], 78_400_000)
        self.assertEqual(a["income_amount"], 313_600_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 311_100_000)
        self.assertEqual(a["rate"], 50)
        self.assertEqual(a["progressive_deduction"], 25_940_000)
        self.assertEqual(a["tax"], 129_610_000)
        self.assertEqual(a["local_tax"], 12_961_000)

    def test_asset_detail(self):
        t = self.t1
        self.assertEqual(t["necessary_expenses"], 308_000_000)
        self.assertEqual(t["holding_years"], 10)
        self.assertEqual(t["holding_rate_pct"], 20)  # 장특 표1, 취득일부터
        self.assertEqual(t["rate_rule"], "non_business")

    def test_basis_for_every_step(self):
        self.assertEqual(set(self.res["basis"]), set(self.amt))
        self.assertIn("§104①8", self.res["basis"]["rate"])
        self.assertIn("§103의3①(+1%p)", self.res["basis"]["local_tax"])


class TestC009Variants(unittest.TestCase):
    """§2 변형."""

    # 취득 2024-02-20 → 양도 2025-08-20 보유 1년 6개월, 장특 0, 경비 0 → 과세표준 = 양도가 − 취득가 − 250만
    SHORT = {"acquisition_date": dt.date(2024, 2, 20), "acquisition_price": 300_000_000, "expenses": 0}

    def test_short_term_40_wins_at_200m(self):
        # 과세표준 2억: 단기 40% 80,000,000 > 기본 38%+10%p 200,000,000×48% − 19,940,000 = 76,060,000
        a, t = compute_with(transfer_price=502_500_000, **self.SHORT)
        self.assertEqual(t["holding_years"], 1)
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["tax_base"], 200_000_000)
        self.assertEqual(t["rate_rule"], "short_term")
        self.assertEqual(a["rate"], 40)
        self.assertEqual(a["tax"], 80_000_000)
        self.assertEqual(a["local_tax"], 8_000_000)

    def test_non_business_wins_at_300m(self):
        # 과세표준 3억: 기본 38%+10%p 300,000,000×48% − 19,940,000 = 124,060,000 > 단기 40% 120,000,000
        a, t = compute_with(transfer_price=602_500_000, **self.SHORT)
        self.assertEqual(a["tax_base"], 300_000_000)
        self.assertEqual(t["rate_rule"], "non_business")
        self.assertEqual(a["rate"], 48)
        self.assertEqual(a["tax"], 124_060_000)
        self.assertEqual(a["local_tax"], 12_406_000)

    def test_business_land_basic_rate(self):
        # 사업용(플래그 false): 311,100,000×40% − 25,940,000 = 98,500,000
        a, t = compute_with(non_business_land=False)
        self.assertEqual(t["rate_rule"], "basic")
        self.assertEqual(a["rate"], 40)
        self.assertEqual(a["tax"], 98_500_000)
        self.assertEqual(a["local_tax"], 9_850_000)

    def test_non_land_flag_out_of_scope(self):
        with self.assertRaises(NotImplementedError):
            compute_with(kind="건물")


if __name__ == "__main__":
    unittest.main()
