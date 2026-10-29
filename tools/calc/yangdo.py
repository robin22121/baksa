"""양도소득세 계산 — 조문 단위 순수 함수 (일반 부동산·1세대1주택·조정 2주택 중과·중과 배제·기본세율 경로).

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

주택 자산(kind: 주택, house: true)은 다음 키를 더 받는다:

          one_house: true                 # 1세대1주택(§89①3, 시행령 §154). false면 범위 밖
          adjusted_area_acquired: true    # 취득 당시 조정대상지역(시행령 §154① 거주요건)
          contract_date: 2018-02-10       # 계약일(기록용. 부칙 예외는 아래 플래그로만 판정)
          residence_exception: false      # 2017-08-02 이전 계약·계약일 무주택 부칙 예외
          residence_start: 2018-04-10     # 거주 시작·종료일 또는 residence_years(정수)
          residence_end: 2025-08-20

1세대1주택이 아닌 주택(one_house: false)은 다음 키를 받고, 1세대2주택 중 아래 셋만 범위 안이다
(결과 자산 행 surcharge_status):

          house_count: 2                  # 세대 주택 수(시행령 §167의10②). 2만 범위 안
          adjusted_area_at_transfer: true # 양도 시점 조정대상지역(§104⑦1)
          transfer_contract_date: 2026-06-01  # 양도 매매계약일(2026-05-10 이후 양도에만 필요)
    - 조정대상지역, 양도일 2022-05-10~2026-05-09 → 중과 배제(시행령 §167의10①12의2), "excluded_grace"
      (기본세율 §104①1 + 장특 표1 §95②)
    - 조정대상지역, 양도일 2026-05-10 이후이고 양도 계약일도 2026-05-10 이후 → 중과, "surcharged"
      (§104⑦1: §55① 세율 + 20%p, 누진공제는 기본표 그대로 / 장특 0 — §95② 본문 괄호).
      자산 1건 양도만 범위 안(같은 해 여러 자산이면 §104⑤ 비교과세 — 범위 밖)
    - 비조정대상지역 → §104⑦ 자산 아님, "not_adjusted" (기본세율 + 장특 표1)
  contract_date는 취득 계약일(1세대1주택 부칙 예외 판정용)이라 양도 계약일과 키를 나눈다.

취득 실지거래가액 불명이면 acquisition_price 대신 다음 키를 받는다(환산취득가액만, §176의2③ 순위는 범위 밖):

          acquisition_price_unknown: true
          transfer_std_price: 560000000     # 양도 당시 기준시가
          acquisition_std_price: 280000000  # 취득 당시 기준시가

범위 밖 분기(입력이 요구하면 NotImplementedError):
3주택 이상, 조정대상지역 2주택의 2022-05-10 이전 양도, 2026-05-09 이전 계약·이후 양도(보완 유예 4~6개월 —
지역별 기간 조문 미확인, 계약금 요건 미반영), 2026-05-10 이후 양도인데 양도 계약일 없음, 중과 자산이 낀 여러 자산 양도,
일시적 2주택·상속주택 등 특례, 2021-06-01 이전 양도의 단기보유(2년 미만) 세율,
단기세율 자산이 낀 여러 자산 양도(§104⑤ 비교과세), 비사업용토지, 그 밖의 중과(surcharge 플래그), 감면, 미등기,
일괄양도 안분, 감가상각비 차감(≠0), 비거주자, 2023-01-01 이전 양도(§55① 옛 세율표).
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

ASSET_KINDS = ("토지", "건물", "주택")

# 소득세법 §89①3 괄호·시행령 §156① 고가주택 기준(2021-12-08 이후 양도분 12억원).
# 그 전 양도(9억)는 2023-01-01 이전 양도 차단(BASIC_RATE_FROM)으로 범위 밖.
HIGH_PRICE_LIMIT = 1_200_000_000
# 시행령 §154①(2017.9.19 개정) 거주요건 — 2017-08-03 이후 조정대상지역 취득분
RESIDENCE_RULE_FROM = _dt.date(2017, 8, 3)
# 주택 중 1세대1주택 외 분기 플래그 → 범위 밖
OTHER_HOUSE_FLAGS = ("temporary_two_house", "inherited_house", "multi_house")
# 시행령 §167의10①12의2 — 보유 2년 이상 조정대상지역 주택을 이 기간에 양도하면 2주택 중과 배제
GRACE_FROM = _dt.date(2022, 5, 10)
GRACE_TO = _dt.date(2026, 5, 9)
# 소득세법 §104①2·3(2020.8.18 개정) — 2021-06-01 이후 양도분 단기세율. (주택%, 그 밖%)
SHORT_TERM_FROM = _dt.date(2021, 6, 1)
SHORT_TERM_RATES = {1: (60, 40), 0: (70, 50)}  # 보유 만 년수 → 2호(1년 이상 2년 미만)·3호(1년 미만)


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
    is_house = bool(asset.get("house"))
    if is_house != (kind == "주택"):
        raise NotImplementedError(f"{aid}: kind={kind!r}·house={asset.get('house')!r} 조합 — 범위 밖")
    if is_house:
        if not asset.get("one_house"):
            surcharge_status(asset)  # 2주택 중과·중과 배제·비조정만 범위 안
        for flag in OTHER_HOUSE_FLAGS:
            if asset.get(flag):
                raise NotImplementedError(f"{aid}: {flag}(시행령 §155 특례 등) — 범위 밖")
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
    if tr < SHORT_TERM_FROM and holding_years(asset["acquisition_date"], tr) < 2:
        raise NotImplementedError(f"{aid}: 2021-06-01 이전 양도 보유 2년 미만 단기세율(§104①2·3 옛 세율) — 범위 밖")
    if tr < BASIC_RATE_FROM:
        raise NotImplementedError(f"{aid}: 2023-01-01 이전 양도 — §55① 옛 세율표 범위 밖")


def surcharge_status(asset: dict) -> str:
    """1세대2주택(one_house: false, house_count 2) 주택의 중과 판정.

    근거: 소득세법 §104⑦1(조정대상지역 1세대2주택 +20%p, 장특 배제 §95② 본문 괄호),
    시행령 §167의10①12의2(보유 2년 이상 주택을 2022-05-10~2026-05-09에 양도 → 중과 배제).
    양도 시점 비조정대상지역이면 §104⑦ 자산이 아님 → "not_adjusted".
    유예기간 안이면 "excluded_grace". 유예는 연장 없이 2026-05-09 종료(2026-02-24 국무회의 의결
    시행령 개정) → 양도일 2026-05-10 이후이고 양도 계약일(transfer_contract_date)도 2026-05-10
    이후면 "surcharged". 계약일 ≤ 2026-05-09(보완 유예 4~6개월)이거나 계약일이 없으면
    NotImplementedError. 그 밖(2022-05-10 이전 양도·3주택 이상)도 NotImplementedError.
    """
    aid = asset.get("id", "?")
    if asset.get("house_count") != 2:
        raise NotImplementedError(
            f"{aid}: 세대 주택 수 {asset.get('house_count')!r}(3주택 이상 §104⑦3·4 등) — 범위 밖")
    if not asset.get("adjusted_area_at_transfer"):
        return "not_adjusted"
    tr = _date(asset["transfer_date"])
    if tr < GRACE_FROM:
        raise NotImplementedError(f"{aid}: 2022-05-10 이전 조정대상지역 2주택 양도 — 중과(§104⑦1) 범위 밖")
    if tr <= GRACE_TO:
        if holding_years(asset["acquisition_date"], tr) < 2:
            raise NotImplementedError(
                f"{aid}: 보유 2년 미만 조정대상지역 2주택 유예기간 양도 — 중과 배제(시행령 §167의10①12의2) "
                "보유 2년 요건 미달, 중과·단기세율 비교 범위 밖")
        return "excluded_grace"
    contract = asset.get("transfer_contract_date")
    if contract is None:
        raise NotImplementedError(
            f"{aid}: 2026-05-10 이후 조정대상지역 2주택 양도 — 양도 계약일(transfer_contract_date) 없음, "
            "보완 유예 해당 여부 판정 불가")
    if _date(contract) <= GRACE_TO:
        raise NotImplementedError(
            f"{aid}: 2026-05-09 이전 계약·이후 양도 — 보완 유예 4~6개월 — 지역별 기간 조문 미확인, "
            "계약금 요건 미반영")
    return "surcharged"


# ---------------------------------------------------------------- 조문 함수

def necessary_expenses(asset: dict) -> int:
    """필요경비 = 취득가액 + 자본적지출액 등 + 양도비 등 − 감가상각비(이번 범위는 0).

    근거: 소득세법 §97①(취득가액·자본적지출·양도비), §97③(사업소득 필요경비로 산입한
    감가상각비 공제), 시행령 §163(필요경비 범위 — 취득세 등 취득부대비용, 중개수수료 등 양도비).
    `expenses`는 항목별 dict(합산) 또는 정수.
    취득가액 불명(acquisition_price_unknown)이면 converted_expenses의 규칙을 따른다.
    """
    if asset.get("acquisition_price_unknown"):
        return converted_expenses(asset)[0]
    exp = asset.get("expenses") or 0
    exp_total = sum(int(v or 0) for v in exp.values()) if isinstance(exp, dict) else int(exp)
    return int(asset["acquisition_price"]) + exp_total - int(asset.get("depreciation") or 0)


def converted_acquisition_price(asset: dict) -> int:
    """환산취득가액 = 양도가액 × 취득 당시 기준시가 ÷ 양도 당시 기준시가.

    근거: 소득세법 §97①1나, 시행령 §163⑫, §176의2②2. 매매사례가액·감정가액 순위(§176의2③)는
    범위 밖 — acquisition_price_unknown은 환산취득가액만 뜻한다.
    원 미만 절사(floor): 가정 — 조문 없음, 미실측.
    """
    return int(asset["transfer_price"]) * int(asset["acquisition_std_price"]) // int(asset["transfer_std_price"])


def estimated_expense(asset: dict) -> int:
    """필요경비 개산공제 = 취득 당시 기준시가 × 3%(등기 토지·건물), 원 미만 절사.

    근거: 소득세법 §97②2호, 시행령 §163⑥1·2호. 미등기(0.3%)는 범위 밖.
    """
    if asset.get("registered") is False:
        raise NotImplementedError(f"{asset.get('id', '?')}: 미등기 개산공제 0.3%(시행령 §163⑥) — 범위 밖")
    return int(asset["acquisition_std_price"]) * 3 // 100


def converted_expenses(asset: dict) -> tuple[int, int, int, str]:
    """취득가액 불명 → (필요경비, 환산취득가액, 개산공제, expense_rule).

    근거: 소득세법 §97②2호 본문(환산취득가액 + 개산공제), 단서(그 합계가 자본적지출액 + 양도비
    합계보다 적으면 후자) → max. 취득세 등 취득부대비용은 환산취득가액에 흡수되므로 따로 넣지 않는다
    (acquisition_tax > 0이면 모호하므로 NotImplementedError). 나머지 expenses 항목(양도비·자본적지출)이
    단서 비교의 실제 경비 쪽.
    """
    aid = asset.get("id", "?")
    exp = asset.get("expenses") or 0
    if isinstance(exp, dict):
        if int(exp.get("acquisition_tax") or 0) > 0:
            raise NotImplementedError(
                f"{aid}: 취득가액 불명(환산취득가액)인데 acquisition_tax 입력 — 필요경비 구분 모호, 범위 밖")
        actual = sum(int(v or 0) for k, v in exp.items() if k != "acquisition_tax")
    else:
        actual = int(exp)
    conv = converted_acquisition_price(asset)
    est = estimated_expense(asset)
    if conv + est >= actual:
        return conv + est, conv, est, "converted"
    return actual, conv, est, "actual_expenses"


def transfer_gain(asset: dict) -> int:
    """양도차익 = 양도가액 − 필요경비 (실지거래가액 기준).

    근거: 소득세법 §95①, §96①(양도가액 = 실지거래가액), §97①(필요경비), §100①(실지거래가액
    기준이면 필요경비도 실지거래가액). 자산별로 계산한다.
    """
    return int(asset["transfer_price"]) - necessary_expenses(asset)


def long_term_rate_pct(years: int) -> int:
    """장기보유특별공제율(%) — 표1(일반).

    근거: 소득세법 §95② 표1 — 3년 이상 4년 미만 6%, 이후 1년마다 2%p 가산, 15년 이상 30%.
    3년 미만 0. (1세대1주택 표2는 long_term_rate_pct_table2)
    """
    if years < 3:
        return 0
    return min(years * 2, 30)


def long_term_rate_pct_table2(holding: int, residence: int) -> tuple[int, int]:
    """장기보유특별공제율(%) — 표2(1세대1주택) → (보유분, 거주분).

    근거: 소득세법 §95② 단서·표2(2021.1.1 이후 양도분) — 보유 3년 이상 연 4%(10년 이상 40%),
    거주 2년 이상(보유 3년 이상인 경우) 연 4%(2년 8%, 10년 이상 40%), 합 최대 80%.
    적용 대상은 시행령 §159의4(보유기간 중 거주 2년 이상인 1세대1주택). 보유 3년 미만이면 0.
    """
    if holding < 3:
        return 0, 0
    h = min(holding * 4, 40)
    r = min(residence * 4, 40) if residence >= 2 else 0
    return h, r


def long_term_deduction(gain: int, years: int) -> int:
    """장기보유특별공제액 = 양도차익 × 표1 공제율, 원 미만 절사.

    근거: 소득세법 §95②(토지·건물, 보유 3년 이상, 미등기 제외), 보유기간 §95④.
    차익이 0 이하면 0. 원 미만 절사는 금액 단위가 원이므로 정수 내림(국고금 관리법 §47의
    10원 미만 절사는 납부 단계 규정이라 여기선 적용하지 않음).
    """
    if gain <= 0:
        return 0
    return gain * long_term_rate_pct(years) // 100


def residence_years(asset: dict) -> int:
    """거주기간(만 년수). residence_years가 있으면 그 값, 없으면 거주 시작·종료일로 계산.

    근거: 시행령 §154⑥(거주기간은 주민등록표 등본상 전입일부터 전출일까지), 기간 계산은
    holding_years와 같이 국세기본법 §4·민법 §157·§160. 보유기간 안의 거주만 센다
    (§95② 표2 '보유기간 중 거주기간', 시행령 §159의4).
    """
    if asset.get("residence_years") is not None:
        return int(asset["residence_years"])
    start, end = asset.get("residence_start"), asset.get("residence_end")
    if start is None or end is None:
        return 0
    acq, tr = _date(asset["acquisition_date"]), _date(asset["transfer_date"])
    s, e = max(_date(start), acq), min(_date(end), tr)
    return holding_years(s, e) if e >= s else 0


def one_house_exempt(asset: dict) -> bool:
    """1세대1주택 비과세 요건 충족 여부(고가주택 안분 전 단계).

    근거: 소득세법 §89①3가목, 시행령 §154① — 양도일 현재 국내 1주택, 보유 2년 이상.
    취득 당시 조정대상지역이고 2017-08-03 이후 취득이면 보유기간 중 거주 2년 이상
    (시행령 §154① 본문 괄호). 2017-08-02 이전 계약·계약일 무주택 세대의 부칙 예외
    (대통령령 제28293호 부칙 §2②)는 입력 플래그 residence_exception으로만 받는다.
    """
    if not asset.get("one_house"):
        return False
    acq, tr = _date(asset["acquisition_date"]), _date(asset["transfer_date"])
    if holding_years(acq, tr) < 2:
        return False
    if asset.get("residence_exception") and asset.get("contract_date") is not None:
        if _date(asset["contract_date"]) >= RESIDENCE_RULE_FROM:
            raise ValueError(f"{asset.get('id')}: residence_exception인데 계약일이 2017-08-03 이후")
    need_residence = (
        bool(asset.get("adjusted_area_acquired"))
        and acq >= RESIDENCE_RULE_FROM
        and not asset.get("residence_exception")
    )
    return not need_residence or residence_years(asset) >= 2


def high_price_taxable_gain(gain: int, transfer_price: int) -> int:
    """고가주택 양도차익 중 과세 부분 = 양도차익 × (양도가액 − 12억) ÷ 양도가액, 원 미만 절사.

    근거: 소득세법 §95③, 시행령 §160①1(2021-12-08 이후 양도분 기준 12억원, 시행령 §156①).
    양도가액이 12억 이하면 0(전액 비과세). 차익 0 이하면 0.
    """
    if gain <= 0 or transfer_price <= HIGH_PRICE_LIMIT:
        return 0
    return gain * (transfer_price - HIGH_PRICE_LIMIT) // transfer_price


def high_price_long_term_deduction(full_deduction: int, transfer_price: int) -> int:
    """고가주택 장기보유특별공제 = 전체 양도차익 기준 장특액 × (양도가액 − 12억) ÷ 양도가액.

    근거: 소득세법 §95③, 시행령 §160①2. 원 미만 절사. (과세 양도차익 × 공제율과의 절사 위치
    차이는 C001에선 0 — 계획서 §0 전제 ⑤, 미검증 분기)
    """
    if full_deduction <= 0 or transfer_price <= HIGH_PRICE_LIMIT:
        return 0
    return full_deduction * (transfer_price - HIGH_PRICE_LIMIT) // transfer_price


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


def computed_tax(tax_base: int, surcharge_pct: int = 0) -> int:
    """산출세액 = 과세표준 × (세율 + 가산세율) − 누진공제, 원 미만 절사.

    근거: 소득세법 §104①1, §55①. 정수 산술 floor(과세표준×세율%/100) − 누진공제.
    중과(§104⑦1)는 "§55①에 따른 세율에 100분의 20을 더한 세율" → 구간 세율 + surcharge_pct,
    누진공제는 기본표 그대로.
    (국고금 관리법 §47 10원 미만 절사는 납부·징수 단계라 산출세액엔 적용하지 않음)
    """
    if tax_base <= 0:
        return 0
    pct, prog = basic_rate(tax_base)
    return tax_base * (pct + surcharge_pct) // 100 - prog


def local_income_tax(tax_base: int, surcharge_pct: int = 0) -> int:
    """지방소득세(양도소득분) 산출세액 = 과세표준 × 지방세율 − 지방 누진공제, 원 미만 절사.

    근거: 지방세법 §103의3①(양도소득 과세표준은 소득세법 과세표준과 같음 — §103의2),
    §103의3① 세율 = §92①(종합소득 지방세율 0.6%~4.5%, 국세 세율의 1/10, 누진공제도 1/10).
    중과 자산(§103의3① — 소득세법 §104⑦ 대응)은 구간 지방세율 + surcharge_pct/10(2%p).
    정수 산술 floor(과세표준×(세율%+가산%)/1000) − 누진공제/10.
    """
    if tax_base <= 0:
        return 0
    pct, prog = basic_rate(tax_base)
    return tax_base * (pct + surcharge_pct) // 1000 - prog // 10


def short_term_rate_pct(asset: dict) -> int | None:
    """단기보유 세율(%) — 보유 2년 이상이면 None.

    근거: 소득세법 §104①2(보유 1년 이상 2년 미만: 주택 100분의 60, 그 밖 100분의 40),
    §104①3(1년 미만: 주택 100분의 70, 그 밖 100분의 50), 2021-06-01 이후 양도분.
    세율 적용 보유기간은 §104② — 취득일부터 양도일까지(holding_years와 같은 계산).
    조합원입주권·분양권은 범위 밖(ASSET_KINDS). 단일세율, 누진공제 없음.
    """
    yrs = holding_years(asset["acquisition_date"], asset["transfer_date"])
    if yrs >= 2:
        return None
    house_pct, other_pct = SHORT_TERM_RATES[yrs]
    return house_pct if asset.get("house") else other_pct


def rate_choice(tax_base: int, surcharge_pct: int, short_pct: int | None) -> dict:
    """§104① 단서 — 1호(기본세율, §104⑦ 중과 포함)와 단기세율에 함께 해당하면 큰 세액.

    단기세율 세액 = floor(과세표준 × 세율%/100), 지방소득세는 같은 선택으로 세율 1/10
    (지방세법 §103의3①). 같으면 1호 쪽.
    → {rule, rate, progressive_deduction, tax, local_tax}
    """
    pct, prog = basic_rate(tax_base)
    rule = "surcharged" if surcharge_pct else "basic"
    out = {"rule": rule, "rate": pct + surcharge_pct, "progressive_deduction": prog,
           "tax": computed_tax(tax_base, surcharge_pct),
           "local_tax": local_income_tax(tax_base, surcharge_pct)}
    if short_pct is None:
        return out
    short_tax = max(tax_base, 0) * short_pct // 100
    if short_tax > out["tax"]:
        out = {"rule": "short_term", "rate": short_pct, "progressive_deduction": 0,
               "tax": short_tax, "local_tax": max(tax_base, 0) * short_pct // 1000}
    return out


# ---------------------------------------------------------------- 전체

def compute(inp: dict) -> dict:
    """케이스 input → 단계별 금액(amounts)·근거(basis)·자산별 내역(assets).

    amounts 키: gain, exempt_gain, taxable_gain, holding_deduction, income_amount,
    basic_deduction, tax_base, rate, progressive_deduction, tax, local_tax.
    gain은 전체 양도차익, taxable_gain은 비과세(1세대1주택·고가주택 안분) 뒤 과세대상 양도차익.
    """
    residency = inp.get("residency", "거주자")
    assets = inp.get("assets") or []
    if not assets:
        raise ValueError("input.assets가 비어 있음")
    for a in assets:
        _check_scope(a, residency)

    per_asset = []
    table2_used = False
    for a in assets:
        yrs = holding_years(a["acquisition_date"], a["transfer_date"])
        g = transfer_gain(a)
        row = {"id": a.get("id"), "kind": a["kind"], "necessary_expenses": necessary_expenses(a),
               "gain": g, "holding_years": yrs}
        if a.get("acquisition_price_unknown"):
            _, conv, est, rule = converted_expenses(a)
            row.update({"converted_acquisition_price": conv, "estimated_expense": est,
                        "expense_rule": rule})
        if a.get("house"):
            res = residence_years(a)
            exempt = one_house_exempt(a)
            price = int(a["transfer_price"])
            taxable = high_price_taxable_gain(g, price) if exempt else g
            status = None if a.get("one_house") else surcharge_status(a)
            # §95② 단서·시행령 §159의4: 1세대1주택이고 보유기간 중 거주 2년 이상이면 표2, 아니면 표1
            if status == "surcharged":
                # §95② 본문 괄호: §104⑦ 각 호 주택(중과 자산)은 장기보유특별공제 배제
                h_pct, r_pct, table = 0, 0, "배제"
            elif a.get("one_house") and res >= 2 and yrs >= 3:
                h_pct, r_pct = long_term_rate_pct_table2(yrs, res)
                table = "표2"
                table2_used = True
            else:
                h_pct, r_pct, table = long_term_rate_pct(yrs), 0, "표1"
            full_ltd = g * (h_pct + r_pct) // 100 if g > 0 else 0
            ltd = high_price_long_term_deduction(full_ltd, price) if exempt else full_ltd
            row.update({"residence_years": res, "one_house_exempt": exempt,
                        "ltd_table": table, "holding_rate_pct": h_pct + r_pct,
                        "holding_part_pct": h_pct, "residence_part_pct": r_pct})
            if status is not None:
                row["surcharge_status"] = status
                if status == "surcharged":
                    row["surcharge_pct"] = 20  # §104⑦1
        else:
            taxable = g
            ltd = long_term_deduction(g, yrs)
            row["holding_rate_pct"] = long_term_rate_pct(yrs)
        row.update({"exempt_gain": g - taxable, "taxable_gain": taxable,
                    "holding_deduction": ltd, "income_amount": taxable - ltd})
        per_asset.append(row)

    surcharged = any(p.get("surcharge_status") == "surcharged" for p in per_asset)
    if surcharged and len(per_asset) > 1:
        raise NotImplementedError("중과 자산이 낀 여러 자산 양도(§104⑤ 비교과세) — 범위 밖, 자산 1건만 범위 안")
    add_pct = 20 if surcharged else 0  # §104⑦1
    short_pcts = [short_term_rate_pct(a) for a in assets]
    short_term = any(p is not None for p in short_pcts)
    if short_term and len(per_asset) > 1:
        raise NotImplementedError("단기세율 자산이 낀 여러 자산 양도(§104⑤ 비교과세) — 범위 밖, 자산 1건만 범위 안")

    gain = sum(p["gain"] for p in per_asset)
    taxable_gain = sum(p["taxable_gain"] for p in per_asset)
    ltd = sum(p["holding_deduction"] for p in per_asset)
    # §102①·②: 양도소득금액은 그룹별 합산(같은 그룹 내 결손은 통산)
    income = sum(p["income_amount"] for p in per_asset)
    bd = basic_deduction(income, inp.get("prior_basic_deduction_used", 0))
    base = max(income - bd, 0)
    choice = rate_choice(base, add_pct, short_pcts[0] if short_term else None)
    short_chosen = choice["rule"] == "short_term"
    for p in per_asset:
        p["rate_rule"] = choice["rule"]
    amounts = {
        "gain": gain,
        "exempt_gain": gain - taxable_gain,
        "taxable_gain": taxable_gain,
        "holding_deduction": ltd,
        "income_amount": income,
        "basic_deduction": bd,
        "tax_base": base,
        "rate": choice["rate"],
        "progressive_deduction": choice["progressive_deduction"],
        "tax": choice["tax"],
        "local_tax": choice["local_tax"],
    }
    basis = {
        "gain": "소득세법 §95①, §96①, §97①·③, §100①, 시행령 §163" + (
            ", §97①1나·②2, 시행령 §163⑥·⑫, §176의2②2"
            if any(a.get("acquisition_price_unknown") for a in assets) else ""),
        "exempt_gain": "소득세법 §89①3, 시행령 §154①(1세대1주택), §95③·시행령 §160①1(고가주택 12억 초과분만 과세)",
        "taxable_gain": "소득세법 §95①·③, 시행령 §160①1",
        "holding_deduction": (
            "소득세법 §95② 본문 괄호 — 중과 자산 장특 배제" if surcharged else
            "소득세법 §95② 단서·표2, 시행령 §159의4·§160①2(고가주택 안분), §95④, 국세기본법 §4·민법 §157·§160"
            if table2_used else
            "소득세법 §95② 표1, §95④(보유기간), 국세기본법 §4·민법 §157·§160"),
        "income_amount": "소득세법 §95①, §102",
        "basic_deduction": "소득세법 §103①1·②",
        "tax_base": "소득세법 §92②",
        "rate": "소득세법 §104⑦1, §55①, 시행령 §167의10①(유예 종료 2026-05-09)" if surcharged else
                "소득세법 §104①1, §55①(2023.1.1 이후)" + (
            ", 시행령 §167의10①12의2(2주택 중과 배제)"
            if any(p.get("surcharge_status") == "excluded_grace" for p in per_asset) else ""),
        "progressive_deduction": "소득세법 §55①",
        "tax": ("소득세법 §104⑦1, §55① (기본세율 + 20%p, 원 미만 절사)" if surcharged else
                "소득세법 §104①1, §55① (원 미만 절사)"),
        "local_tax": "지방세법 §103의2, §103의3①, §92① (원 미만 절사)" + (
            ", 중과 자산 지방세율 + 2%p" if surcharged else ""),
    }
    if short_chosen:
        basis.update({
            "rate": "소득세법 §104①2·3·단서(1호 세액과 비교해 큰 것), §104②(보유기간)",
            "progressive_deduction": "소득세법 §104①2·3 (단일세율, 누진공제 없음)",
            "tax": "소득세법 §104①2·3·단서 (과세표준 × 단기세율, 원 미만 절사)",
            "local_tax": "지방세법 §103의2, §103의3① (단기세율 1/10, 원 미만 절사)",
        })
    elif short_term:
        for k in ("rate", "tax"):
            basis[k] += ", §104① 단서(단기세율 §104①2·3 세액보다 큼)"
    return {"amounts": amounts, "basis": basis, "assets": per_asset}
