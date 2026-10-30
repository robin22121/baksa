"""C007 계산 검증 — 상수는 docs/work-plans/2026-10-30-C007-배우자증여-이월과세.md §0 법령 기대값·§2 대조 8항목.

변형(§4-1): 기간 밖(2018-01-01 증여), 경계 쌍(2022-12-31·2023-01-01 증여 → 2029-12-31 양도),
§97의2②3 미적용(not_applied_lower), 증여세 상당액≠0 필요경비.
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

CASE = ROOT / "cases" / "house" / "C007.yaml"


def load_input(case=CASE):
    return yaml.safe_load(case.read_text(encoding="utf-8"))["input"]


def compute_with(case=CASE, **changes):
    inp = copy.deepcopy(load_input(case))
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC007(unittest.TestCase):
    """§2 대조 8항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_eight_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 496_000_000)
        self.assertEqual(a["holding_deduction"], 128_960_000)
        self.assertEqual(a["income_amount"], 367_040_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 364_540_000)
        self.assertEqual(a["rate"], 40)
        self.assertEqual(a["progressive_deduction"], 25_940_000)
        self.assertEqual(a["tax"], 119_876_000)
        self.assertEqual(a["local_tax"], 11_987_600)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["carryover"], "applied")
        self.assertEqual(h["necessary_expenses"], 304_000_000)  # 증여자 취득가액 + 양도비
        self.assertEqual(h["holding_years"], 13)  # 장특: 증여자 취득일부터(§95④ 단서)
        self.assertEqual(h["rate_holding_years"], 13)  # 세율: 증여자 취득일부터(§104②2)
        self.assertEqual(h["holding_rate_pct"], 26)
        self.assertEqual(h["surcharge_status"], "not_adjusted")
        self.assertEqual(h["rate_rule"], "basic")

    def test_basis_for_every_step(self):
        b = self.res["basis"]
        self.assertEqual(set(b), set(self.amt))
        self.assertIn("§97의2①(증여자 취득가액, 증여세 상당액 필요경비)", b["gain"])
        self.assertIn("§95④ 단서(증여자 취득일부터)", b["holding_deduction"])
        self.assertIn("§104②2", b["rate"])
        self.assertIn("§97의2②3(결정세액 비교)", b["tax"])


class TestC007Variants(unittest.TestCase):
    """§4-1 변형."""

    def test_out_of_period_2018_gift(self):
        # 2023-01-01 전 증여 → 5년. 2018-01-01 증여, 2025-08-20 양도 → 기간 밖, 증여가액 600,000,000 기준
        a, h = compute_with(gift_date=dt.date(2018, 1, 1), acquisition_date=dt.date(2018, 1, 1))
        self.assertEqual(h["carryover"], "out_of_period")
        self.assertEqual(h["necessary_expenses"], 604_000_000)
        self.assertEqual(a["gain"], 196_000_000)
        self.assertEqual(h["holding_years"], 7)  # 증여일부터

    # 경계 쌍: 2029-12-31 양도는 현행 세율표·장특표가 그대로라고 가정한다(법령 미래 변경 미반영).
    def test_boundary_gift_2022_12_31_five_years(self):
        _, h = compute_with(gift_date=dt.date(2022, 12, 31), acquisition_date=dt.date(2022, 12, 31),
                            transfer_date=dt.date(2029, 12, 31))
        self.assertEqual(h["carryover"], "out_of_period")

    def test_boundary_gift_2023_01_01_ten_years(self):
        _, h = compute_with(gift_date=dt.date(2023, 1, 1), acquisition_date=dt.date(2023, 1, 1),
                            transfer_date=dt.date(2029, 12, 31))
        self.assertEqual(h["carryover"], "applied")

    def test_not_applied_lower(self):
        # 증여자 취득 700,000,000 → 적용 세액 10,689,600 < 미적용 53,590,000 → 미적용(§97의2②3)
        a, h = compute_with(donor_acquisition_price=700_000_000)
        self.assertEqual(h["carryover"], "not_applied_lower")
        self.assertEqual(a["tax"], 53_590_000)
        self.assertEqual(h["necessary_expenses"], 604_000_000)
        self.assertEqual(h["holding_years"], 2)

    def test_gift_tax_attributable_expense(self):
        a, h = compute_with(gift_tax_attributable=10_000_000)
        self.assertEqual(h["carryover"], "applied")
        self.assertEqual(h["necessary_expenses"], 314_000_000)
        self.assertEqual(a["gain"], 486_000_000)

    def test_one_house_out_of_scope(self):
        with self.assertRaises(NotImplementedError):
            compute_with(one_house=True, house_count=1)

    def test_multi_asset_out_of_scope(self):
        inp = copy.deepcopy(load_input())
        inp["assets"].append(dict(inp["assets"][0], id="H2"))
        with self.assertRaises(NotImplementedError):
            yangdo.compute(inp)


if __name__ == "__main__":
    unittest.main()
