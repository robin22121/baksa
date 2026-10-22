"""케이스 yaml의 input으로 calc를 돌려 expected_law를 채우고 expected_baksa와 대조한다.

사용: python tools/compare.py cases/basic/C000.yaml

- 대조 8항목: 양도차익, 장기보유특별공제, 양도소득금액, 기본공제, 과세표준, 세율, 산출세액, 지방소득세
- status: 8항목이 모두 있으면 match/mismatch, 하나라도 비면 pending
- yaml의 다른 키·주석은 보존한다(최상위 `expected_law:`·`status:` 블록만 글자 단위로 바꾼다)
- 불일치 원인 판정(mismatch_note)은 사람(메인)이 쓴다
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calc import yangdo  # noqa: E402

ITEMS = [
    ("gain", "양도차익"),
    ("holding_deduction", "장기보유특별공제"),
    ("income_amount", "양도소득금액"),
    ("basic_deduction", "기본공제"),
    ("tax_base", "과세표준"),
    ("rate", "세율(%)"),
    ("tax", "산출세액"),
    ("local_tax", "지방소득세"),
]


def _norm(key: str, v):
    """화면에서 읽은 값 정규화: '1,234' → 1234, '38%'·'38'·0.38 → 38."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str):
        s = v.replace(",", "").replace("%", "").replace("원", "").strip()
        v = float(s) if "." in s else int(s)
    if key == "rate" and isinstance(v, float) and v < 1:
        v = v * 100
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return v


def replace_top_block(text: str, key: str, body: str) -> str:
    """최상위 `key:` 줄부터 다음 최상위 키 직전까지를 `body`로 바꾼다(없으면 끝에 붙임)."""
    lines = text.splitlines(keepends=True)
    top = re.compile(r"^[A-Za-z_][\w-]*:")
    start = next((i for i, ln in enumerate(lines) if ln.startswith(f"{key}:")), None)
    if not body.endswith("\n"):
        body += "\n"
    if start is None:
        if text and not text.endswith("\n"):
            text += "\n"
        return text + body
    end = start + 1
    while end < len(lines) and not top.match(lines[end]):
        end += 1
    # 다음 키 바로 위의 주석·빈 줄은 다음 키 소속으로 남긴다
    while end - 1 > start and lines[end - 1].lstrip().startswith("#") and not lines[end - 1].startswith(" "):
        end -= 1
    return "".join(lines[:start]) + body + "".join(lines[end:])


def _keep_comment(text: str, key: str) -> str:
    m = re.search(rf"^{key}:[^\n#]*(#[^\n]*)", text, re.M)
    return f"  {m.group(1)}" if m else ""


def run(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    case = yaml.safe_load(text)
    result = yangdo.compute(case["input"])
    law = result["amounts"]
    baksa = case.get("expected_baksa") or {}

    rows = []
    for key, label in ITEMS:
        b = _norm(key, baksa.get(key))
        l = law[key]
        st = "pending" if b is None else ("match" if b == l else "mismatch")
        rows.append((label, l, b, st, result["basis"][key]))
    states = {r[3] for r in rows}
    # 하나라도 안 읽혔으면 pending(불일치 항목은 표에 남는다), 전부 읽혔으면 match/mismatch
    status = "pending" if "pending" in states else ("mismatch" if "mismatch" in states else "match")

    law_doc = {
        "amounts": {k: law[k] for k in law},
        "assets": result["assets"],
        "basis": result["basis"],
    }
    dumped = yaml.safe_dump(law_doc, allow_unicode=True, sort_keys=False, default_flow_style=False)
    body = "expected_law:" + _keep_comment(text, "expected_law") + "\n" + textwrap.indent(dumped, "  ")
    text = replace_top_block(text, "expected_law", body)
    text = replace_top_block(text, "status", f"status: {status}" + _keep_comment(text, "status") + "\n")
    path.write_text(text, encoding="utf-8")

    print(f"{case.get('case_id')}  law_date={case.get('law_date')}  status={status}")
    print(f"{'항목':<12}{'calc(법령)':>16}{'양도박사':>16}  {'판정':<9}근거")
    for label, l, b, st, bs in rows:
        bs_txt = "-" if b is None else f"{b:,}"
        print(f"{label:<12}{l:>16,}{bs_txt:>16}  {st:<9}{bs}")
    print("자산별:")
    for a in result["assets"]:
        print(f"  {a['id']} {a['kind']}: 필요경비 {a['necessary_expenses']:,} 차익 {a['gain']:,} "
              f"보유 {a['holding_years']}년 {a['holding_rate_pct']}% 장특 {a['holding_deduction']:,}")
    return {"status": status, "rows": rows}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    run(Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
