"""C008 계산 검증 — 상수는 docs/work-plans/2026-10-30-C008-일시적2주택.md §0 법령 기대값·§2 대조 10항목.

변형(§4-1): 1년 요건만 위반(신규 2020-04-30·양도 2023-04-01), 3년 요건만 위반(신규 2021-06-01),
경계(초일불산입 해석 — 확인 필요), 2023-01-12 이전 양도 범위 밖.
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

CASE = ROOT / "cases" / "house" / "C008.yaml"


def load_input(case=CASE):
    return yaml.safe_load(case.read_text(encoding="utf-8"))["input"]


def compute_with(case=CASE, **changes):
    inp = copy.deepcopy(load_input(case))
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC008(unittest.TestCase):
    """§2 대조 10항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_ten_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 786_300_000)
        self.assertEqual(a["exempt_gain"], 629_040_000)
        self.assertEqual(a["taxable_gain"], 157_260_000)
        self.assertEqual(a["holding_deduction"], 75_484_800)
        self.assertEqual(a["income_amount"], 81_775_200)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 79_275_200)
        self.assertEqual(a["rate"], 24)
        self.assertEqual(a["progressive_deduction"], 5_760_000)
        self.assertEqual(a["tax"], 13_266_048)
        self.assertEqual(a["local_tax"], 1_326_604)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["one_house_special"], "§155①")
        self.assertTrue(h["one_house_exempt"])
        self.assertEqual(h["ltd_table"], "표2")
        self.assertEqual(h["holding_years"], 6)
        self.assertEqual(h["residence_years"], 6)
        self.assertEqual(h["holding_rate_pct"], 48)
        self.assertNotIn("surcharge_status", h)

    def test_basis(self):
        b = self.res["basis"]
        self.assertEqual(set(b), set(self.amt))
        self.assertIn("시행령 §155①(일시적 2주택)", b["exempt_gain"])
        self.assertIn("표2", b["holding_deduction"])


class TestC008Variants(unittest.TestCase):
    """§4-1 변형."""

    def test_one_year_rule_only_violated(self):
        # 신규 2020-04-30 < 종전 취득 2019-05-01 + 1년 → 미충족. 양도 2023-04-01은 신규+3년 이내.
        # 마포 해제(2023-01-05) 후 양도 → 비조정 2주택 일반, 보유 3년 11개월 → 표1 6%
        a, h = compute_with(new_house_acquisition_date=dt.date(2020, 4, 30),
                            transfer_date=dt.date(2023, 4, 1), residence_end=dt.date(2023, 4, 1))
        self.assertIsNone(h["one_house_special"])
        self.assertFalse(h["one_house_exempt"])
        self.assertEqual(h["surcharge_status"], "not_adjusted")
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(h["holding_years"], 3)
        self.assertEqual(h["holding_rate_pct"], 6)
        self.assertEqual(a["gain"], 786_300_000)
        self.assertEqual(a["exempt_gain"], 0)
        self.assertEqual(a["holding_deduction"], 47_178_000)
        self.assertEqual(a["income_amount"], 739_122_000)
        self.assertEqual(a["tax_base"], 736_622_000)
        self.assertEqual(a["rate"], 42)
        self.assertEqual(a["tax"], 273_441_240)
        self.assertEqual(a["local_tax"], 27_344_124)

    def test_three_year_rule_only_violated(self):
        # 신규 2021-06-01 → 3년 뒤 2024-06-01 < 양도 2025-08-20 → 미충족. 비조정 2주택 일반, 보유 6년 → 표1 12%
        a, h = compute_with(new_house_acquisition_date=dt.date(2021, 6, 1))
        self.assertIsNone(h["one_house_special"])
        self.assertFalse(h["one_house_exempt"])
        self.assertEqual(h["surcharge_status"], "not_adjusted")
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(h["holding_rate_pct"], 12)
        self.assertEqual(a["exempt_gain"], 0)
        self.assertEqual(a["holding_deduction"], 94_356_000)
        self.assertEqual(a["income_amount"], 691_944_000)
        self.assertEqual(a["tax_base"], 689_444_000)
        self.assertEqual(a["rate"], 42)
        self.assertEqual(a["tax"], 253_626_480)
        self.assertEqual(a["local_tax"], 25_362_648)

    def test_boundary_one_year_same_day(self):
        # 확인 필요: 초일불산입 — 신규 = 종전 취득 + 1년 당일이면 충족으로 본다
        # (양도 2023-04-01로 3년 요건은 충족)
        _, h = compute_with(new_house_acquisition_date=dt.date(2020, 5, 1),
                            transfer_date=dt.date(2023, 4, 1), residence_end=dt.date(2023, 4, 1))
        self.assertEqual(h["one_house_special"], "§155①")

    def test_boundary_three_years_same_day(self):
        # 확인 필요: 초일불산입 — 양도 = 신규 취득 + 3년 당일이면 충족, 다음날이면 미충족으로 본다
        _, h = compute_with(new_house_acquisition_date=dt.date(2022, 8, 20))
        self.assertEqual(h["one_house_special"], "§155①")
        _, h = compute_with(new_house_acquisition_date=dt.date(2022, 8, 19))
        self.assertIsNone(h["one_house_special"])

    def test_old_house_residence_not_met(self):
        # 종전주택 조정 취득분 거주 2년 미달 → §154① 미충족 → 일시적 2주택 아님
        _, h = compute_with(residence_end=dt.date(2020, 5, 1))
        self.assertIsNone(h["one_house_special"])
        self.assertFalse(h["one_house_exempt"])

    def test_before_2023_01_12_out_of_scope(self):
        with self.assertRaises(NotImplementedError):
            compute_with(transfer_date=dt.date(2023, 1, 11), residence_end=dt.date(2023, 1, 11))

    def test_missing_new_house_date(self):
        with self.assertRaises(NotImplementedError):
            compute_with(new_house_acquisition_date=None)


if __name__ == "__main__":
    unittest.main()
