"""양도소득세 계산 — 조문 단위 순수 함수 (일반 부동산·기본세율 경로).

금액은 전부 정수(원). 세율 곱은 정수 산술로 하고 원 미만은 버린다(아래 각 함수 참조).

입력(케이스 yaml `input`) 구조:

    input:
      residency: 거주자
      prior_basic_deduction_used: 0      # 같은 해 같은 그룹(부동산 등)에서 이미 쓴 기본공제
      assets:
        - id: L1
          kind: 토지                     # 토지 | 건물(주택 외)
          transfer_date: 2025-06-30
          acquisition_date: 2020-03-16
          transfer_price: 600000000
          acquisition_price: 400000000
          expenses: {acquisition_tax: 18400000, transfer_brokerage: 5400000}
          depreciation: 0
          registered: true
          house: false
          non_business_land: false
          surcharge: false
          reduction: null
          price_basis: 구분가액           # 구분가액 | 안분(일괄양도 기준시가 안분 — 범위 밖)

범위 밖 분기(입력이 요구하면 NotImplementedError):
1세대1주택·주택, 단기보유(2년 미만) 세율, 비사업용토지, 중과, 감면, 미등기, 일괄양도 안분,
감가상각비 차감(≠0), 비거주자, 2023-01-01 이전 양도(§55① 옛 세율표).
"""

from __future__ import annotations

import calendar
import datetime as _dt
from typing import Any

NotInScope = NotImplementedError

BASIC_DEDUCTION = 2_500_000

# 소득세법 §55① (2022.12.31 개정, 2023.1.1 이후 양도분부터). (상한, 세율%, 누진공제)
BASIC_RATE_TABLE = (
    (14_000_000, 6, 0),
    (50_000_000, 15, 1_260_000),
    (88_000_000, 24, 5_760_000),
    (150_000_000, 35, 15_440_000),
    (300_000_000, 38, 19_940_000),
    (500_000_000, 40, 25_940_000),
    (1_000_000_000, 42, 35_940_000),
    (None, 45, 65_940_000),
)
BASIC_RATE_FROM = _dt.date(2023, 1, 1)

ASSET_KINDS = ("토지", "건물")


# ---------------------------------------------------------------- 공통

def _date(v: Any) -> _dt.date:
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    return _dt.date.fromisoformat(str(v))


def _add_years(start: _dt.date, n: int) -> _dt.date | None:
    """start의 n년 뒤 같은 월·일. 그런 날이 없으면(2월 29일) None."""
    try:
        return start.replace(year=start.year + n)
    except ValueError:
        return None


def holding_years(acquisition_date: Any, transfer_date: Any) -> int:
    """보유기간(만 년수).

    근거: 소득세법 §95④ — 보유기간은 그 자산의 취득일부터 양도일까지로 한다.
    기간 계산은 국세기본법 §4(세법에 특별한 규정이 없으면 민법에 따름) → 민법 §157 초일불산입
    (기산일 = 취득일 다음날), 민법 §160②(연으로 정한 기간은 역에 의해 계산, 기산일에 해당하는
    날의 전날로 만료), §160③(해당 날이 없으면 그 월의 말일로 만료).

    결과적으로 '취득일의 n년 뒤 같은 날'에 n년이 찬다(예: 2020-03-16 취득 → 2023-03-16 양도
    시 3년). 취득·양도일은 §98·시행령 §162(잔금청산일 등)로 이미 정해진 날짜를 받는다.
    """
    acq, tr = _date(acquisition_date), _date(transfer_date)
    if tr < acq:
        raise ValueError(f"양도일 {tr}이 취득일 {acq}보다 앞섬")
    start = acq + _dt.timedelta(days=1)  # 초일불산입
    years = 0
    while True:
        n = years + 1
        anniv = _add_years(start, n)
        if anniv is None:  # 기산일이 2/29, 해당 연도에 2/29 없음 → 그 월 말일(2/28)로 만료
            y = start.year + n
            end = _dt.date(y, 2, calendar.monthrange(y, 2)[1])
        else:
            end = anniv - _dt.timedelta(days=1)
        if end <= tr:
            years = n
        else:
            return years


def _check_scope(asset: dict, residency: str) -> None:
    """이번 범위 밖 분기를 막는다. 근거 조문은 메시지에 적는다."""
    aid = asset.get("id", "?")
    if residency != "거주자":
        raise NotImplementedError(f"{aid}: 비거주자(§118의2~) — 범위 밖")
    kind = asset.get("kind")
    if kind not in ASSET_KINDS:
        raise NotImplementedError(f"{aid}: 자산 종류 {kind!r} — 범위 밖(토지·건물만)")
    if asset.get("house"):
        raise NotImplementedError(f"{aid}: 주택(1세대1주택 §89①3, 중과 §104⑦, 장특 표2) — 범위 밖")
    if asset.get("registered") is False:
        raise NotImplementedError(f"{aid}: 미등기(§104①10, §95② 단서, §103① 단서) — 범위 밖")
    if asset.get("non_business_land"):
        raise NotImplementedError(f"{aid}: 비사업용토지(§104①8, §104의3) — 범위 밖")
    if asset.get("surcharge"):
        raise NotImplementedError(f"{aid}: 중과(§104④·⑦) — 범위 밖")
    if asset.get("reduction"):
        raise NotImplementedError(f"{aid}: 감면(조세특례제한법) — 범위 밖")
    if asset.get("price_basis", "구분가액") != "구분가액":
        raise NotImplementedError(f"{aid}: 일괄양도 기준시가 안분(§100②·③, 시행령 §166⑥) — 범위 밖")
    if int(asset.get("depreciation") or 0) != 0:
        raise NotImplementedError(f"{aid}: 감가상각비 차감(§97③) — 범위 밖")
    tr = _date(asset["transfer_date"])
    if tr < BASIC_RATE_FROM:
        raise NotImplementedError(f"{aid}: 2023-01-01 이전 양도 — §55① 옛 세율표 범위 밖")
    if holding_years(asset["acquisition_date"], tr) < 2:
        raise NotImplementedError(f"{aid}: 보유 2년 미만 단기세율(§104①2·3) — 범위 밖")


# ---------------------------------------------------------------- 조문 함수

def necessary_expenses(asset: dict) -> int:
    """필요경비 = 취득가액 + 자본적지출액 등 + 양도비 등 − 감가상각비(이번 범위는 0).

    근거: 소득세법 §97①(취득가액·자본적지출·양도비), §97③(사업소득 필요경비로 산입한
    감가상각비 공제), 시행령 §163(필요경비 범위 — 취득세 등 취득부대비용, 중개수수료 등 양도비).
    `expenses`는 항목별 dict(합산) 또는 정수.
    """
    exp = asset.get("expenses") or 0
    exp_total = sum(int(v or 0) for v in exp.values()) if isinstance(exp, dict) else int(exp)
    return int(asset["acquisition_price"]) + exp_total - int(asset.get("depreciation") or 0)


def transfer_gain(asset: dict) -> int:
    """양도차익 = 양도가액 − 필요경비 (실지거래가액 기준).

    근거: 소득세법 §95①, §96①(양도가액 = 실지거래가액), §97①(필요경비), §100①(실지거래가액
    기준이면 필요경비도 실지거래가액). 자산별로 계산한다.
    """
    return int(asset["transfer_price"]) - necessary_expenses(asset)


def long_term_rate_pct(years: int) -> int:
    """장기보유특별공제율(%) — 표1(일반).

    근거: 소득세법 §95② 표1 — 3년 이상 4년 미만 6%, 이후 1년마다 2%p 가산, 15년 이상 30%.
    3년 미만 0. (1세대1주택 표2는 범위 밖)
    """
    if years < 3:
        return 0
    return min(years * 2, 30)


def long_term_deduction(gain: int, years: int) -> int:
    """장기보유특별공제액 = 양도차익 × 표1 공제율, 원 미만 절사.

    근거: 소득세법 §95②(토지·건물, 보유 3년 이상, 미등기 제외), 보유기간 §95④.
    차익이 0 이하면 0. 원 미만 절사는 금액 단위가 원이므로 정수 내림(국고금 관리법 §47의
    10원 미만 절사는 납부 단계 규정이라 여기선 적용하지 않음).
    """
    if gain <= 0:
        return 0
    return gain * long_term_rate_pct(years) // 100


def basic_deduction(income: int, already_used: int = 0) -> int:
    """양도소득 기본공제 — 부동산 등 그룹(§94①1·2·4)별 연 2,500,000원.

    근거: 소득세법 §103①1(그룹별 연 250만원, 미등기 제외), §103②(감면 외 소득에서 먼저,
    그 안에선 먼저 양도한 자산부터). 이번 범위는 같은 해 같은 그룹 합산 소득에서 1회 공제.
    """
    remain = max(BASIC_DEDUCTION - int(already_used or 0), 0)
    return min(remain, max(income, 0))


def basic_rate(tax_base: int) -> tuple[int, int]:
    """기본세율 구간 → (세율%, 누진공제액).

    근거: 소득세법 §104①1(보유 2년 이상 일반 자산 → §55① 세율), §55①(2023.1.1 이후 표).
    """
    for limit, pct, prog in BASIC_RATE_TABLE:
        if limit is None or tax_base <= limit:
            return pct, prog
    raise AssertionError("unreachable")


def computed_tax(tax_base: int) -> int:
    """산출세액 = 과세표준 × 세율 − 누진공제, 원 미만 절사.

    근거: 소득세법 §104①1, §55①. 정수 산술 floor(과세표준×세율%/100) − 누진공제.
    (국고금 관리법 §47 10원 미만 절사는 납부·징수 단계라 산출세액엔 적용하지 않음)
    """
    if tax_base <= 0:
        return 0
    pct, prog = basic_rate(tax_base)
    return tax_base * pct // 100 - prog


def local_income_tax(tax_base: int) -> int:
    """지방소득세(양도소득분) 산출세액 = 과세표준 × 지방세율 − 지방 누진공제, 원 미만 절사.

    근거: 지방세법 §103의3①(양도소득 과세표준은 소득세법 과세표준과 같음 — §103의2),
    §103의3① 세율 = §92①(종합소득 지방세율 0.6%~4.5%, 국세 세율의 1/10, 누진공제도 1/10).
    정수 산술 floor(과세표준×세율%/1000) − 누진공제/10.
    """
    if tax_base <= 0:
        return 0
    pct, prog = basic_rate(tax_base)
    return tax_base * pct // 1000 - prog // 10


# ---------------------------------------------------------------- 전체

def compute(inp: dict) -> dict:
    """케이스 input → 단계별 금액(amounts)·근거(basis)·자산별 내역(assets).

    amounts 키: gain, holding_deduction, income_amount, basic_deduction, tax_base, rate,
    progressive_deduction, tax, local_tax.
    """
    residency = inp.get("residency", "거주자")
    assets = inp.get("assets") or []
    if not assets:
        raise ValueError("input.assets가 비어 있음")
    for a in assets:
        _check_scope(a, residency)

    per_asset = []
    for a in assets:
        yrs = holding_years(a["acquisition_date"], a["transfer_date"])
        g = transfer_gain(a)
        ltd = long_term_deduction(g, yrs)
        per_asset.append({
            "id": a.get("id"),
            "kind": a["kind"],
            "necessary_expenses": necessary_expenses(a),
            "gain": g,
            "holding_years": yrs,
            "holding_rate_pct": long_term_rate_pct(yrs),
            "holding_deduction": ltd,
            "income_amount": g - ltd,
        })

    gain = sum(p["gain"] for p in per_asset)
    ltd = sum(p["holding_deduction"] for p in per_asset)
    # §102①·②: 양도소득금액은 그룹별 합산(같은 그룹 내 결손은 통산)
    income = sum(p["income_amount"] for p in per_asset)
    bd = basic_deduction(income, inp.get("prior_basic_deduction_used", 0))
    base = max(income - bd, 0)
    pct, prog = basic_rate(base)
    amounts = {
        "gain": gain,
        "holding_deduction": ltd,
        "income_amount": income,
        "basic_deduction": bd,
        "tax_base": base,
        "rate": pct,
        "progressive_deduction": prog,
        "tax": computed_tax(base),
        "local_tax": local_income_tax(base),
    }
    basis = {
        "gain": "소득세법 §95①, §96①, §97①·③, §100①, 시행령 §163",
        "holding_deduction": "소득세법 §95② 표1, §95④(보유기간), 국세기본법 §4·민법 §157·§160",
        "income_amount": "소득세법 §95①, §102",
        "basic_deduction": "소득세법 §103①1·②",
        "tax_base": "소득세법 §92②",
        "rate": "소득세법 §104①1, §55①(2023.1.1 이후)",
        "progressive_deduction": "소득세법 §55①",
        "tax": "소득세법 §104①1, §55① (원 미만 절사)",
        "local_tax": "지방세법 §103의2, §103의3①, §92① (원 미만 절사)",
    }
    return {"amounts": amounts, "basis": basis, "assets": per_asset}
