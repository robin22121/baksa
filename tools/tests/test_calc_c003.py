"""C003 계산 검증 — 상수는 docs/work-plans/2026-10-29-C003-조정2주택-중과.md §0 법령 기대값·§2 대조 8항목.

변형(§2): 양도·계약 2026-05-10(중과 첫날), 계약 2026-05-09·양도 2026-07-20(보완 유예 → 범위 밖),
비조정 양도(not_adjusted, 기본세율·표1), 중과 자산이 낀 여러 자산 양도(범위 밖).
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

CASE = ROOT / "cases" / "house" / "C003.yaml"


def load_input():
    return yaml.safe_load(CASE.read_text(encoding="utf-8"))["input"]


def compute_with(**changes):
    inp = copy.deepcopy(load_input())
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC003(unittest.TestCase):
    """§2 대조 8항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_eight_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 390_500_000)
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["income_amount"], 390_500_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 388_000_000)
        self.assertEqual(a["rate"], 60)
        self.assertEqual(a["progressive_deduction"], 25_940_000)
        self.assertEqual(a["tax"], 206_860_000)
        self.assertEqual(a["local_tax"], 20_686_000)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["necessary_expenses"], 509_500_000)
        self.assertEqual(h["holding_years"], 11)
        self.assertEqual(h["surcharge_status"], "surcharged")
        self.assertEqual(h["surcharge_pct"], 20)
        self.assertEqual(h["ltd_table"], "배제")
        self.assertEqual(h["holding_rate_pct"], 0)

    def test_basis_for_every_step(self):
        self.assertEqual(set(self.res["basis"]), set(self.amt))
        self.assertIn("§104⑦1", self.res["basis"]["rate"])
        self.assertIn("§95② 본문 괄호", self.res["basis"]["holding_deduction"])


class TestC003Variants(unittest.TestCase):
    """§2 변형."""

    def test_surcharge_first_day(self):
        # 양도·계약 모두 2026-05-10 → 유예 종료 뒤, 보완 유예 아님 → 중과
        a, h = compute_with(transfer_date=dt.date(2026, 5, 10), transfer_contract_date=dt.date(2026, 5, 10))
        self.assertEqual(h["surcharge_status"], "surcharged")
        self.assertEqual(a["holding_deduction"], 0)
        self.assertEqual(a["rate"], 60)
        self.assertEqual(a["tax"], 206_860_000)
        self.assertEqual(a["local_tax"], 20_686_000)

    def test_contract_before_grace_end_out_of_scope(self):
        # 계약 2026-05-09·양도 2026-07-20 → 보완 유예(4~6개월) 분기 — 지역별 기간 조문 미확인
        with self.assertRaisesRegex(NotImplementedError, "보완 유예"):
            compute_with(transfer_contract_date=dt.date(2026, 5, 9))

    def test_missing_contract_date_out_of_scope(self):
        with self.assertRaisesRegex(NotImplementedError, "양도 계약일"):
            compute_with(transfer_contract_date=None)

    def test_not_adjusted_basic_rate_table1(self):
        # 양도 시점 비조정 → §104⑦ 자산 아님: 기본세율 + 장특 표1(보유 11년 22%)
        a, h = compute_with(adjusted_area_at_transfer=False)
        self.assertEqual(h["surcharge_status"], "not_adjusted")
        self.assertNotIn("surcharge_pct", h)
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(h["holding_rate_pct"], 22)
        self.assertEqual(a["holding_deduction"], 85_910_000)
        self.assertEqual(a["income_amount"], 304_590_000)
        self.assertEqual(a["tax_base"], 302_090_000)
        self.assertEqual(a["rate"], 40)
        self.assertEqual(a["tax"], 94_896_000)
        self.assertEqual(a["local_tax"], 9_489_600)

    def test_mixed_assets_out_of_scope(self):
        # 중과 자산 + 일반 토지 같은 해 양도 → §104⑤ 비교과세 범위 밖
        inp = copy.deepcopy(load_input())
        inp["assets"].append({
            "id": "L1", "kind": "토지", "transfer_date": dt.date(2026, 8, 1),
            "acquisition_date": dt.date(2015, 1, 1), "transfer_price": 100_000_000,
            "acquisition_price": 50_000_000, "expenses": 0, "depreciation": 0,
            "registered": True, "house": False})
        with self.assertRaisesRegex(NotImplementedError, "비교과세"):
            yangdo.compute(inp)


if __name__ == "__main__":
    unittest.main()
