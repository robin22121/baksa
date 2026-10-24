"""C001 계산 검증 — 상수는 docs/work-plans/2026-10-24-C001-고가주택.md §0 법령 기대값·§2 대조 10항목.

경계 변형(§2): 양도가 11.9억 / 거주 1년 / 보유 2년 11개월 / 비조정 취득.
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

CASE = ROOT / "cases" / "house" / "C001.yaml"


def load_input():
    return yaml.safe_load(CASE.read_text(encoding="utf-8"))["input"]


def compute_with(**changes):
    inp = copy.deepcopy(load_input())
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC001(unittest.TestCase):
    """§2 대조 10항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_ten_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 685_200_000)
        self.assertEqual(a["exempt_gain"], 548_160_000)
        self.assertEqual(a["taxable_gain"], 137_040_000)
        self.assertEqual(a["holding_deduction"], 76_742_400)
        self.assertEqual(a["income_amount"], 60_297_600)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 57_797_600)
        self.assertEqual(a["rate"], 24)
        self.assertEqual(a["progressive_deduction"], 5_760_000)
        self.assertEqual(a["tax"], 8_111_424)
        self.assertEqual(a["local_tax"], 811_142)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["holding_years"], 7)
        self.assertEqual(h["residence_years"], 7)
        self.assertTrue(h["one_house_exempt"])
        self.assertEqual(h["ltd_table"], "표2")
        self.assertEqual((h["holding_part_pct"], h["residence_part_pct"]), (28, 28))

    def test_basis_for_every_step(self):
        self.assertEqual(set(self.res["basis"]), set(self.amt))


class TestC001Boundaries(unittest.TestCase):
    """§2 경계 변형 4개."""

    def test_price_under_limit_fully_exempt(self):
        # 11.9억 ≤ 12억 → 고가주택 아님, 전액 비과세(시행령 §156①, §154①)
        a, h = compute_with(transfer_price=1_190_000_000)
        self.assertEqual(a["gain"], 375_200_000)
        self.assertEqual(a["exempt_gain"], 375_200_000)
        self.assertEqual(a["taxable_gain"], 0)
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["basic_deduction"], 0)
        self.assertEqual(a["tax"], 0)
        self.assertEqual(a["local_tax"], 0)

    def test_residence_one_year_table1(self):
        # 조정지역 취득·거주 1년 → 거주요건 미충족으로 비과세 불가(시행령 §154①), 장특은 표1 7년 14%
        a, h = compute_with(residence_start=dt.date(2024, 8, 20))
        self.assertEqual(h["residence_years"], 1)
        self.assertFalse(h["one_house_exempt"])
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(h["holding_rate_pct"], 14)
        self.assertEqual(a["taxable_gain"], 685_200_000)
        self.assertEqual(a["holding_deduction"], 95_928_000)

    def test_residence_one_year_non_adjusted_table1(self):
        # 비조정 취득·거주 1년 → 비과세(고가 안분)되지만 장특은 표1 14%(§95② 단서·시행령 §159의4)
        a, h = compute_with(residence_start=dt.date(2024, 8, 20), adjusted_area_acquired=False)
        self.assertTrue(h["one_house_exempt"])
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(a["taxable_gain"], 137_040_000)
        self.assertEqual(a["holding_deduction"], 19_185_600)

    def test_holding_2y11m(self):
        # 보유·거주 2년 11개월: 보유 2년·거주 2년 충족 → 비과세 요건 충족(§154①), 12억 초과분 과세.
        # 보유 3년 미만이라 장특 0(§95②). 계획서 §2의 "비과세 불가"와 다름 — 보고 대상.
        acq = dt.date(2022, 9, 20)
        a, h = compute_with(acquisition_date=acq, contract_date=dt.date(2022, 8, 1),
                            residence_start=acq)
        self.assertEqual(h["holding_years"], 2)
        self.assertTrue(h["one_house_exempt"])
        self.assertEqual(a["taxable_gain"], 137_040_000)
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["tax_base"], 134_540_000)
        self.assertEqual(a["tax"], 31_649_000)

    def test_holding_2y11m_residence_short_not_exempt(self):
        # 보유 2년 11개월·조정지역·거주 1년 → 비과세 불가, 전액 과세, 장특 0
        acq = dt.date(2022, 9, 20)
        a, h = compute_with(acquisition_date=acq, residence_start=dt.date(2024, 8, 20))
        self.assertFalse(h["one_house_exempt"])
        self.assertEqual(a["taxable_gain"], 685_200_000)
        self.assertEqual(a["holding_deduction"], 0)

    def test_non_adjusted_no_residence_requirement(self):
        # 비조정 취득 → 거주요건 없음(시행령 §154①), 거주 0 → 비과세(고가 안분), 장특 표1 14%
        a, h = compute_with(adjusted_area_acquired=False, residence_start=None, residence_end=None)
        self.assertEqual(h["residence_years"], 0)
        self.assertTrue(h["one_house_exempt"])
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(a["exempt_gain"], 548_160_000)
        self.assertEqual(a["taxable_gain"], 137_040_000)
        self.assertEqual(a["holding_deduction"], 19_185_600)
        # 같은 조건에서 조정지역 취득이면 비과세 불가(대조)
        a2, h2 = compute_with(residence_start=None, residence_end=None)
        self.assertFalse(h2["one_house_exempt"])
        self.assertEqual(a2["taxable_gain"], 685_200_000)


class TestHouseRules(unittest.TestCase):
    def test_table2_rates(self):
        self.assertEqual(yangdo.long_term_rate_pct_table2(2, 2), (0, 0))
        self.assertEqual(yangdo.long_term_rate_pct_table2(3, 2), (12, 8))
        self.assertEqual(yangdo.long_term_rate_pct_table2(12, 11), (40, 40))

    def test_residence_exception_flag(self):
        a, h = compute_with(residence_start=None, residence_end=None, residence_exception=True,
                            contract_date=dt.date(2017, 7, 1))
        self.assertTrue(h["one_house_exempt"])
        with self.assertRaises(ValueError):
            compute_with(residence_exception=True)  # 계약일 2018-02-10과 모순

    def test_other_house_branches_out_of_scope(self):
        for ch in ({"one_house": False}, {"temporary_two_house": True},
                   {"inherited_house": True}, {"surcharge": True}):
            with self.subTest(ch=ch), self.assertRaises(NotImplementedError):
                compute_with(**ch)


if __name__ == "__main__":
    unittest.main()
