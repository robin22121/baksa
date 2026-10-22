"""C000 계산 검증 — 상수는 docs/work-plans/2026-10-22-C000-2단계.md §0 법령 기대값(Fable 검산).

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

CASE = ROOT / "cases" / "basic" / "C000.yaml"


def load_input():
    return yaml.safe_load(CASE.read_text(encoding="utf-8"))["input"]


class TestC000(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inp = load_input()
        cls.res = yangdo.compute(cls.inp)
        cls.amt = cls.res["amounts"]

    def test_asset_gains(self):
        by_id = {a["id"]: a for a in self.res["assets"]}
        self.assertEqual(by_id["L1"]["gain"], 176_200_000)
        self.assertEqual(by_id["B1"]["gain"], 41_300_000)
        self.assertEqual(by_id["L1"]["holding_years"], 5)
        self.assertEqual(by_id["B1"]["holding_rate_pct"], 10)

    def test_amounts(self):
        a = self.amt
        self.assertEqual(a["gain"], 217_500_000)
        self.assertEqual(a["holding_deduction"], 21_750_000)
        self.assertEqual(a["income_amount"], 195_750_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 193_250_000)
        self.assertEqual(a["rate"], 38)
        self.assertEqual(a["progressive_deduction"], 19_940_000)
        self.assertEqual(a["tax"], 53_495_000)
        self.assertEqual(a["local_tax"], 5_349_500)

    def test_basis_for_every_step(self):
        self.assertEqual(set(self.res["basis"]), set(self.amt))


class TestHoldingYears(unittest.TestCase):
    def test_anniversary(self):
        # 초일불산입: 취득일의 n년 뒤 같은 날에 n년이 찬다
        self.assertEqual(yangdo.holding_years(dt.date(2020, 3, 16), dt.date(2023, 3, 15)), 2)
        self.assertEqual(yangdo.holding_years(dt.date(2020, 3, 16), dt.date(2023, 3, 16)), 3)

    def test_leap_day_start(self):
        # 2020-02-28 취득 → 기산일 2020-02-29, 1년 만료는 2021-02-28(민법 §160③)
        self.assertEqual(yangdo.holding_years(dt.date(2020, 2, 28), dt.date(2021, 2, 27)), 0)
        self.assertEqual(yangdo.holding_years(dt.date(2020, 2, 28), dt.date(2021, 2, 28)), 1)

    def test_rate_table(self):
        self.assertEqual(yangdo.long_term_rate_pct(2), 0)
        self.assertEqual(yangdo.long_term_rate_pct(3), 6)
        self.assertEqual(yangdo.long_term_rate_pct(15), 30)
        self.assertEqual(yangdo.long_term_rate_pct(20), 30)


class TestOutOfScope(unittest.TestCase):
    def _with(self, **changes):
        inp = copy.deepcopy(load_input())
        inp["assets"][0].update(changes)
        return inp

    def test_depreciation(self):
        with self.assertRaises(NotImplementedError):
            yangdo.compute(self._with(depreciation=1_000_000))

    def test_short_holding(self):
        with self.assertRaises(NotImplementedError):
            yangdo.compute(self._with(acquisition_date=dt.date(2024, 1, 1)))

    def test_house_and_non_business_land(self):
        for ch in ({"house": True}, {"non_business_land": True}, {"price_basis": "안분"}):
            with self.subTest(ch=ch), self.assertRaises(NotImplementedError):
                yangdo.compute(self._with(**ch))


if __name__ == "__main__":
    unittest.main()
