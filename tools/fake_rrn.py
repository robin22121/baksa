"""가상 주민등록번호 생성기 (검증숫자가 맞는 13자리).

형식 YYMMDD-GSSSSSC: G=성별·세기(1900년대 남 1·여 2, 2000년대 남 3·여 4), SSSSS=생년월일·성별에서
해시로 정한 5자리(같은 인자 → 항상 같은 번호), C=검증숫자.
검증숫자: 앞 12자리에 가중치 2,3,4,5,6,7,8,9,2,3,4,5를 곱해 더한 합 S에 대해 C = (11 - S % 11) % 10.

가상 납세자 전용이다. 실존 번호와 우연히 겹칠 수 있으므로 실제 신고·전송에 쓰지 않는다(CLAUDE.md 데이터 절).

사용: python tools/fake_rrn.py [--birth 1985-05-05] [--sex M|F]
"""
import argparse
import datetime
import hashlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)

# 검증 공식 재현용 풀이 예시: 880101-123456 의 검증숫자는 8 (합 146, 146 % 11 = 3, 11 - 3 = 8).
EXAMPLE_FIRST12 = "880101123456"
EXAMPLE_CHECK = 8


def check_digit(first12):
    """앞 12자리 문자열 → 검증숫자(정수)."""
    if len(first12) != 12 or not first12.isdigit():
        raise ValueError(f"앞 12자리 숫자가 아님: {first12!r}")
    s = sum(int(d) * w for d, w in zip(first12, WEIGHTS))
    return (11 - s % 11) % 10


def verify(rrn):
    """13자리(하이픈 허용)의 검증숫자가 맞으면 True."""
    d = rrn.replace("-", "")
    return len(d) == 13 and d.isdigit() and check_digit(d[:12]) == int(d[12])


def _to_date(birth):
    if isinstance(birth, datetime.datetime):
        return birth.date()
    if isinstance(birth, datetime.date):
        return birth
    return datetime.date.fromisoformat(str(birth))


def make(birth="1985-05-05", sex="M"):
    """생년월일(date 또는 'YYYY-MM-DD')·성별('M'/'F') → 숫자만 13자리. 같은 인자에는 항상 같은 값."""
    b = _to_date(birth)
    s = str(sex).upper()[:1]
    if s not in ("M", "F"):
        raise ValueError(f"성별은 M 또는 F: {sex!r}")
    if not 1900 <= b.year <= 2099:
        raise ValueError(f"연도 범위 1900~2099: {b.year}")
    g = (1 if s == "M" else 2) + (2 if b.year >= 2000 else 0)
    serial = int(hashlib.sha256(f"{b.isoformat()}|{s}".encode()).hexdigest()[:8], 16) % 100000
    first12 = f"{b.year % 100:02d}{b.month:02d}{b.day:02d}{g}{serial:05d}"
    return first12 + str(check_digit(first12))


def fmt(rrn13):
    return f"{rrn13[:6]}-{rrn13[6:]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--birth", default="1985-05-05", help="생년월일 YYYY-MM-DD (기본 1985-05-05)")
    ap.add_argument("--sex", default="M", choices=["M", "F", "m", "f"], help="성별 (기본 M)")
    args = ap.parse_args()

    r = make(args.birth, args.sex)
    c = check_digit(r[:12])
    print(f"주민번호: {fmt(r)}")
    print(f"검증숫자 재계산: 앞 12자리 {r[:12]} → {c}, 13번째 자리 {r[12]} → {'일치' if c == int(r[12]) else '불일치'}")
    assert verify(r), "생성 번호 검증 실패"
    again = make(args.birth, args.sex)
    print(f"같은 인자 재생성: {'동일' if again == r else '다름'}")

    got = check_digit(EXAMPLE_FIRST12)
    s = sum(int(d) * w for d, w in zip(EXAMPLE_FIRST12, WEIGHTS))
    print(f"공식 재현(풀이 예시 880101-123456): 합 {s}, {s} % 11 = {s % 11}, 11 - {s % 11} = {11 - s % 11} → 검증숫자 {got} "
          f"(기대 {EXAMPLE_CHECK}) {'일치' if got == EXAMPLE_CHECK else '불일치'}")
    return 0 if (c == int(r[12]) and again == r and got == EXAMPLE_CHECK) else 1


if __name__ == "__main__":
    sys.exit(main())
