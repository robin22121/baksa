"""C002 계산 검증 — 상수는 docs/work-plans/2026-10-28-C002-조정2주택-중과유예.md §0 법령 기대값·§2 대조 8항목.

경계 변형(§2): 양도일 2022-05-09 / 2022-05-10 / 2026-05-09 / 2026-05-10, 비조정 양도, 3주택, 보유 1년 11개월.
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

CASE = ROOT / "cases" / "house" / "C002.yaml"


def load_input():
    return yaml.safe_load(CASE.read_text(encoding="utf-8"))["input"]


def compute_with(**changes):
    inp = copy.deepcopy(load_input())
    inp["assets"][0].update(changes)
    res = yangdo.compute(inp)
    return res["amounts"], res["assets"][0]


class TestC002(unittest.TestCase):
    """§2 대조 8항목."""

    @classmethod
    def setUpClass(cls):
        cls.res = yangdo.compute(load_input())
        cls.amt = cls.res["amounts"]
        cls.h1 = cls.res["assets"][0]

    def test_eight_items(self):
        a = self.amt
        self.assertEqual(a["gain"], 390_500_000)
        self.assertEqual(a["holding_deduction"], 78_100_000)
        self.assertEqual(a["income_amount"], 312_400_000)
        self.assertEqual(a["basic_deduction"], 2_500_000)
        self.assertEqual(a["tax_base"], 309_900_000)
        self.assertEqual(a["rate"], 40)
        self.assertEqual(a["progressive_deduction"], 25_940_000)
        self.assertEqual(a["tax"], 98_020_000)
        self.assertEqual(a["local_tax"], 9_802_000)

    def test_asset_detail(self):
        h = self.h1
        self.assertEqual(h["necessary_expenses"], 509_500_000)
        self.assertEqual(h["holding_years"], 10)
        self.assertFalse(h["one_house_exempt"])
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(h["holding_rate_pct"], 20)
        self.assertEqual(h["surcharge_status"], "excluded_grace")

    def test_basis_for_every_step(self):
        self.assertEqual(set(self.res["basis"]), set(self.amt))


class TestC002Boundaries(unittest.TestCase):
    """§2 경계 변형."""

    def test_grace_first_day_blocked_by_old_rate_table(self):
        # 2022-05-10은 유예 첫날(시행령 §167의10①12의2)이라 중과 판정은 통과하지만,
        # 2023-01-01 이전 양도라 §55① 옛 세율표가 calc 범위 밖 → NotImplementedError(옛 세율표 사유)
        with self.assertRaisesRegex(NotImplementedError, "옛 세율표"):
            compute_with(transfer_date=dt.date(2022, 5, 10))
        h = dict(load_input()["assets"][0], transfer_date=dt.date(2022, 5, 10))
        self.assertEqual(yangdo.surcharge_status(h), "excluded_grace")

    def test_grace_last_day_excluded(self):
        # 2026-05-09 유예 마지막 날 → 중과 배제, 보유 11년 → 표1 22%
        a, h = compute_with(transfer_date=dt.date(2026, 5, 9))
        self.assertEqual(h["surcharge_status"], "excluded_grace")
        self.assertEqual(h["holding_years"], 11)
        self.assertEqual(h["ltd_table"], "표1")
        self.assertEqual(a["holding_deduction"], 85_910_000)
        self.assertEqual(a["tax_base"], 302_090_000)
        self.assertEqual(a["rate"], 40)
        self.assertEqual(a["tax"], 94_896_000)

    def test_before_grace_out_of_scope(self):
        # 2022-05-09 → 유예 전, 중과(§104⑦1) 범위 밖
        with self.assertRaisesRegex(NotImplementedError, "2022-05-10 이전"):
            compute_with(transfer_date=dt.date(2022, 5, 9))

    def test_after_grace_needs_contract_date(self):
        # 2026-05-10 양도(유예 종료 뒤, C003 계획서 §0) — 양도 계약일이 없거나 2026-05-09 이전이면
        # 보완 유예 해당 여부를 판정할 수 없어 NotImplementedError. 계약일도 5-10 이후면 중과.
        with self.assertRaisesRegex(NotImplementedError, "양도 계약일"):
            compute_with(transfer_date=dt.date(2026, 5, 10))
        with self.assertRaisesRegex(NotImplementedError, "보완 유예"):
            compute_with(transfer_date=dt.date(2026, 5, 10), transfer_contract_date=dt.date(2026, 5, 9))
        a, h = compute_with(transfer_date=dt.date(2026, 5, 10), transfer_contract_date=dt.date(2026, 5, 10))
        self.assertEqual(h["surcharge_status"], "surcharged")
        self.assertEqual(a["rate"], 60)

    def test_not_adjusted_same_result(self):
        # 양도 시점 비조정대상지역 → §104⑦ 자산 아님, C002와 같은 결과
        a, h = compute_with(adjusted_area_at_transfer=False)
        self.assertEqual(h["surcharge_status"], "not_adjusted")
        self.assertEqual(a, yangdo.compute(load_input())["amounts"])
        self.assertEqual(a["tax"], 98_020_000)

    def test_three_houses_out_of_scope(self):
        with self.assertRaises(NotImplementedError):
            compute_with(house_count=3)

    def test_holding_1y11m_out_of_scope(self):
        # 보유 1년 11개월 → 단기세율(§104①2) 범위 밖
        with self.assertRaisesRegex(NotImplementedError, "보유 2년 미만"):
            compute_with(acquisition_date=dt.date(2023, 9, 21), contract_date=dt.date(2023, 8, 1))


if __name__ == "__main__":
    unittest.main()
