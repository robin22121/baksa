"""메뉴 트리 순회 + 화면마다 캡처·컨트롤 덤프 (W1b). 읽기 전용.

저장·확인·전송·삭제 버튼은 누르지 않는다. 금지 메뉴는 App.click_menu가 거른다.
"""
import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as appmod  # noqa: E402

ROOT = appmod.ROOT
SCREENS = ROOT / "docs" / "screens"
RAW = ROOT / "docs" / "inventory" / "raw"
FLOW = RAW / "flow.jsonl"

CONTROL_TYPES = ("Edit", "Button", "ComboBox", "CheckBox", "RadioButton", "DataGrid", "Table", "List", "Pane")


def next_seq():
    last = 0
    if FLOW.exists():
        for line in FLOW.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = max(last, json.loads(line).get("seq", 0))
    return last + 1


def slug(path):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "_", "_".join(path)).strip("_")


def read_menu_tree(main):
    """uia MenuBar/MenuItem 기준 트리: [{'text':..., 'children':[...]}]"""
    # TODO(win): win32 백엔드 폴백 (main.menu().items() 재귀). 서브메뉴는 열어야 보이는 경우 있음
    bar = main.child_window(control_type="MenuBar")

    def walk(item):
        node = {"text": item.window_text(), "children": []}
        try:
            for sub in item.children(control_type="MenuItem"):
                node["children"].append(walk(sub))
        except Exception:  # noqa: BLE001
            pass
        return node

    return [walk(i) for i in bar.children(control_type="MenuItem")]


def leaves(nodes, prefix=()):
    for n in nodes:
        p = prefix + (n["text"],)
        if n["children"]:
            yield from leaves(n["children"], p)
        elif n["text"]:
            yield list(p)


def count_controls(win):
    counts = {}
    for t in CONTROL_TYPES:
        try:
            n = len(win.descendants(control_type=t))
        except Exception:  # noqa: BLE001
            n = 0
        if n:
            counts[t] = n
    return counts


def capture(a, path_menu, seq):
    # TODO(win): 새로 뜬 창이 top_window인지 확인. 없으면 메인 창을 대상으로 한다
    win = a.app.top_window()
    nn = f"{seq:02d}"
    SCREENS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    try:
        win.capture_as_image().save(SCREENS / f"{nn}_{slug(path_menu)}.png")
    except Exception as e:  # noqa: BLE001
        appmod.log("capture", f"실패 {nn}: {e}")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            win.print_control_identifiers()
    except Exception as e:  # noqa: BLE001
        buf.write(f"덤프 실패: {e}\n")
    (RAW / f"screen_{nn}.txt").write_text(buf.getvalue(), encoding="utf-8")
    rec = {"seq": seq, "menu_path": path_menu, "window_title": win.window_text(), "controls": count_controls(win)}
    with FLOW.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="양도박사")
    ap.add_argument("--backend", choices=["uia", "win32"], default="uia")
    ap.add_argument("--max", type=int, default=0, help="리프 메뉴 처리 상한(디버그)")
    ap.add_argument("--dry-run", action="store_true", help="메뉴 트리만 출력, 클릭 없음")
    args = ap.parse_args()

    ok, why = appmod.available()
    if not ok:
        print(f"{why} — 종료 (Windows + pywinauto 필요)")
        return 0

    a = appmod.App()
    main_win = a.attach(args.title, args.backend)
    tree = read_menu_tree(main_win)
    paths = list(leaves(tree))
    if args.dry_run:
        for p in paths:
            mark = "  [금지]" if any(a.is_forbidden(s) for s in p) else ""
            print(" > ".join(p) + mark)
        return 0

    seq = next_seq()
    done = 0
    for p in paths:
        if args.max and done >= args.max:
            break
        if not a.click_menu(p):
            continue
        rec = capture(a, p, seq)
        print(f"{seq:02d} {' > '.join(p)} -> {rec['window_title']!r} {rec['controls']}")
        seq += 1
        done += 1
        a.dismiss_modal()  # TODO(win): 닫히지 않으면 사람이 확인. 메인 창 복귀 검증 추가
    return 0


if __name__ == "__main__":
    sys.exit(main())
