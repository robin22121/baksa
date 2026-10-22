"""양도소득세 조문 단위 계산 모듈.

- 계산 기준은 소득세법 §94~§118·시행령, 지방세법 §103의3이다(양도박사가 아니다).
- 이번 범위: 일반 부동산(토지·주택외 건물), 2년 이상 보유, 기본세율(§104①1·§55①).
  그 밖의 분기는 NotImplementedError로 막는다.
"""

from .yangdo import compute, holding_years, NotInScope  # noqa: F401
