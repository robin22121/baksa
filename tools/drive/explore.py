"""버튼 트리 순회 + 화면마다 캡처·컨트롤 덤프 (W1b). 허용 목록(allow.yaml)에 있는 버튼만 누른다.

--dry-run: 루트 화면의 버튼을 허용/금지/unreviewed로 분류해 출력만 한다.
종료 코드: 정상 0, 중단 2, 예외 1. 정의는 docs/work-plans/2026-10-22-설치형-탐색기.md §2.
"""
import argparse
import hashlib
import json
import re
import sys
import time
import traceback
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as appmod  # noqa: E402
import yaml  # noqa: E402

ROOT = appmod.ROOT
SCREENS = ROOT / "docs" / "screens"
RAW = ROOT / "docs" / "inventory" / "raw"
FLOW = RAW / "flow.jsonl"
ALLOW = Path(__file__).resolve().parent / "allow.yaml"

MAX_SCREENS, MAX_PRESSES, MAX_SECONDS = 60, 300, 30 * 60
EDGE_WAIT = 5.0
KEEP_TYPES = {"Button", "Edit", "ComboBox", "CheckBox", "RadioButton", "DataGrid", "Table", "List", "Tab", "TabItem", "Text"}


class Abort(Exception):
    pass


def clean_title(t):
    """데모 문구('▶ 본 프로그램은 데모버전' 이후)를 지운 제목."""
    return t.split("▶")[0].strip()


def slug(s):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "_", s).strip("_")[:40]


def load_allow():
    d = yaml.safe_load(ALLOW.read_text(encoding="utf-8")) or {}
    return {
        "root": appmod.norm(d.get("root", "")),
        "screens": {appmod.norm(k): [appmod.norm(b) for b in v] for k, v in (d.get("screens") or {}).items()},
        "modals": {appmod.norm(k): [appmod.norm(b) for b in v] if isinstance(v, list) else [appmod.norm(v)]
                   for k, v in (d.get("modals") or {}).items()},
    }


def next_seq():
    last = 0
    if FLOW.exists():
        for line in FLOW.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = max(last, json.loads(line).get("seq", 0))
    return last + 1


def classify(a, allow, title, names):
    """버튼 이름 → (허용, 금지, unreviewed). 금지가 허용보다 우선. 이름은 원문 기준, 중복 제거."""
    allowed_set = set(allow["screens"].get(appmod.norm(clean_title(title)), []))
    ok, banned, unrev, seen = [], [], [], set()
    for n in names:
        k = appmod.norm(n)
        if k in seen:
            continue
        seen.add(k)
        if a.is_forbidden(n):
            banned.append(n)
        elif k in allowed_set:
            ok.append(n)
        else:
            unrev.append(n)
    return ok, banned, unrev


def controls_of(hwnd):
    """컨트롤 덤프. uia가 예외이거나 10초 넘으면 win32 descendants로 대체(source 표시). (목록, source)"""
    def uia():
        out = []
        for c in appmod.wrap(hwnd).descendants():
            e = c.element_info
            if e.control_type in KEEP_TYPES:
                r = e.rectangle
                out.append({"type": e.control_type, "name": e.name, "auto_id": e.automation_id,
                            "rect": [r.left, r.top, r.right, r.bottom], "enabled": bool(e.enabled)})
        return out
    try:
        return appmod.call_with_timeout(uia, 10), "uia"
    except Exception as e:  # noqa: BLE001
        appmod.log("controls_of", f"uia 실패 → win32 {e}")
        out = []
        for d in appmod.win32_descendants(hwnd):
            r = d.rectangle()
            out.append({"type": d.class_name(), "name": d.window_text(),
                        "rect": [r.left, r.top, r.right, r.bottom]})
        return out, "win32"


def screen_key(title, cls, names):
    h = hashlib.sha1("|".join([title, cls] + sorted(appmod.norm(n) for n in names)).encode("utf-8"))
    return h.hexdigest()[:8]


def find_root_screen(a, root_name):
    for w in a.screens_info():
        if w.hwnd != a.main_hwnd and appmod.norm(clean_title(w.title)) == root_name:
            return w
    return None


class Run:
    def __init__(self, a, allow):
        self.a, self.allow = a, allow
        self.t0 = time.time()
        self.seq = next_seq()
        self.visited = {}
        self.presses = 0
        self.nscreens = 0
        self.unreviewed = 0
        self.errors = 0
        self.externals = []
        self.unknown_modal = False
        self.start_screens = set(a.screens())  # 실행 전부터 열려 있던 화면은 닫지 않는다

    def check_limits(self):
        if self.nscreens >= MAX_SCREENS:
            raise Abort(f"화면 상한 {MAX_SCREENS}")
        if self.presses >= MAX_PRESSES:
            raise Abort(f"누르기 상한 {MAX_PRESSES}")
        if time.time() - self.t0 > MAX_SECONDS:
            raise Abort("시간 상한 30분")

    def flow(self, rec):
        RAW.mkdir(parents=True, exist_ok=True)
        with FLOW.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def record(self, hwnd, path, parent_seq, edge, kind="screen"):
        """창 하나를 캡처·덤프하고 flow에 한 줄 쓴다. (seq, key, 허용 버튼) 반환."""
        seq = self.seq
        self.seq += 1
        info = next((w for w in self.a.screens_info() + self.a.modals_info() if w.hwnd == hwnd), None)
        title = info.title if info else ""
        cls = info.cls if info else ""
        names = self.a.buttons(hwnd)
        key = screen_key(clean_title(title), cls, names)
        ok, banned, unrev = classify(self.a, self.allow, title, names)
        name = f"{seq:03d}_{slug(clean_title(title) or kind)}_{slug(edge)}"
        cap = self.a.capture(hwnd, SCREENS / f"{name}.png")
        ctrls, source = controls_of(hwnd)
        counts = {}
        for c in ctrls:
            counts[c["type"]] = counts.get(c["type"], 0) + 1
        RAW.mkdir(parents=True, exist_ok=True)
        (RAW / f"{name}.json").write_text(json.dumps(
            {"seq": seq, "path": path, "title": title, "key": key, "rect": list(appmod.window_rect(hwnd)),
             "edge": edge, "capture": cap, "source": source, "controls": ctrls, "unreviewed": unrev, "blocked": banned},
            ensure_ascii=False, indent=1), encoding="utf-8")
        self.flow({"seq": seq, "path": path, "title": title, "key": key, "parent_seq": parent_seq,
                   "edge": edge, "counts": counts})
        self.nscreens += 1
        self.unreviewed += len(unrev)
        print(f"{seq:03d} [{kind}/{edge}] {clean_title(title)!r} key={key} 허용={len(ok)} 금지={len(banned)} unreviewed={len(unrev)} cap={cap}")
        return seq, key, ok

    def handle_modals(self, new_modals, parent_seq, path):
        """새 모달 처리. 알려진 모달이면 지정 버튼을 누르고, 처음 보는 모달이면 캡처하고 Abort."""
        for m in new_modals:
            w = next((x for x in self.a.modals_info() if x.hwnd == m), None)
            known = self.allow["modals"].get(self.a.modal_key(w)) if w else None
            seq, _, _ = self.record(m, path + ["[모달]"], parent_seq, "modal", kind="modal")
            if known is None:
                self.unknown_modal = True
                raise Abort(f"처음 보는 모달 {w.title if w else m!r} (seq {seq}) — modals에 추가 필요")
            for b in known:
                self.a.press(m, b)
            appmod.wait_for(lambda: m not in self.a.modals(), 3)

    def snapshot(self):
        return set(self.a.screens()), set(self.a.modals()), set(self.a.externals())

    def after_press(self, before):
        """누른 뒤 최대 EDGE_WAIT초 관찰. (새 화면, 새 모달, 새 external) 반환."""
        def diff():
            s, m, e = self.snapshot()
            return s - before[0], m - before[1], e - before[2]
        appmod.wait_for(lambda: any(diff()), EDGE_WAIT)
        time.sleep(0.6)  # 창이 완전히 뜨기를 잠깐 더 기다림
        return diff()

    def note_external(self, new_ext, path, parent_seq):
        ext = self.a.externals()
        for h in new_ext:
            t, p = ext.get(h, ("", ""))
            self.externals.append({"title": t, "process": p})
            self.flow({"seq": self.seq, "path": path, "title": t, "key": "", "parent_seq": parent_seq,
                       "edge": "external", "counts": {}, "process": p})
            self.seq += 1
            print(f"    external: {t!r} ({p}) — 닫지 않음, 보고 필요")

    def close_child(self, hwnd, parent_seq, path):
        """자식 화면 닫기. 닫으며 모달이 뜨면 모달 규칙 적용."""
        before = self.snapshot()
        self.a.close_screen(hwnd, timeout=1.5)
        new_m = set(self.a.modals()) - before[1]
        if new_m:
            self.handle_modals(new_m, parent_seq, path + ["[닫기]"])
            if hwnd in self.a.screens():
                self.a.close_screen(hwnd)

    def visit(self, hwnd, path, parent_seq, edge):
        self.check_limits()
        info = next((w for w in self.a.screens_info() if w.hwnd == hwnd), None)
        names = self.a.buttons(hwnd)
        key = screen_key(clean_title(info.title), info.cls, names) if info else ""
        if key in self.visited:
            self.flow({"seq": self.seq, "path": path, "title": info.title, "key": key, "parent_seq": parent_seq,
                       "edge": edge, "counts": {}, "dup_of": self.visited[key]})
            self.seq += 1
            print(f"    (이미 방문한 화면 key={key} — 펼치지 않음)")
            return
        seq, key, allowed = self.record(hwnd, path, parent_seq, edge)
        self.visited[key] = seq
        for btn in allowed:
            self.check_limits()
            self.step(hwnd, btn, path + [btn], seq)

    def step(self, parent_hwnd, btn, path, parent_seq):
        """부모 화면에서 버튼 하나를 눌러 간선을 판정하고 처리한다."""
        before = self.snapshot()
        self.presses += 1
        try:
            if not self.a.press(parent_hwnd, btn):
                raise RuntimeError(f"press 실패: {btn}")
            new_s, new_m, new_e = self.after_press(before)
            if new_e:
                self.note_external(new_e, path, parent_seq)
            if new_m:
                self.handle_modals(new_m, parent_seq, path)
                return
            if new_s:
                for h in new_s:
                    self.visit(h, path, parent_seq, "window")
                    self.close_child(h, parent_seq, path)
                if parent_hwnd not in self.a.screens():
                    raise Abort("자식을 닫은 뒤 부모 창이 보이지 않음")
            elif not new_e:
                self.record(parent_hwnd, path, parent_seq, "inplace")
        except Abort:
            raise
        except Exception as e:  # noqa: BLE001
            self.errors += 1
            self.flow({"seq": self.seq, "path": path, "title": "", "key": "", "parent_seq": parent_seq,
                       "edge": "error", "counts": {}, "error": str(e)})
            self.seq += 1
            print(f"    오류: {path} — {e}")


def open_root(a, allow):
    """루트 화면이 이미 열려 있으면 그 창을 쓰고, 아니면 메인에서 루트 버튼을 1회 누른다. (Win, 우리가 열었는지)"""
    w = find_root_screen(a, allow["root"])
    if w:
        return w, False
    before = set(a.screens())
    if not a.press(a.main_hwnd, allow["root"]):
        raise RuntimeError(f"루트 버튼을 누를 수 없음: {allow['root']}")
    appmod.wait_for(lambda: set(a.screens()) - before, EDGE_WAIT)
    time.sleep(0.8)
    w = find_root_screen(a, allow["root"])
    if not w:
        raise RuntimeError("루트 화면이 열리지 않음")
    return w, True


def dry_run(a, allow):
    w, opened = open_root(a, allow)
    names = a.buttons(w.hwnd)
    ok, banned, unrev = classify(a, allow, w.title, names)
    print(f"화면: {clean_title(w.title)!r} (hwnd={w.hwnd}, {'이번에 연 창' if opened else '이미 열려 있던 창 — 누르지 않음'})")
    print(f"버튼 {len(names)}개")
    print("허용      :", [appmod.norm(n) for n in ok])
    print("금지      :", [appmod.norm(n) for n in banned])
    print("unreviewed:", [appmod.norm(n) for n in unrev])
    want = set(allow["screens"].get(appmod.norm(clean_title(w.title)), []))
    miss = want - {appmod.norm(n) for n in ok}
    if miss:
        print("허용 목록에는 있으나 화면에 없음/금지됨:", sorted(miss))
    if opened:
        a.close_screen(w.hwnd)
        print("연 화면을 닫음. 남은 화면:", a.screens(), "모달:", a.modals())
    return 0


def fdb_blocks(root, bdir, changed, page=4096, limit=50):
    """content 변경된 .fdb마다 백업본과 바이트 비교해 달라진 4096바이트 블록 번호(최대 50개). 백업에 없으면 생략."""
    out = {}
    for rel in changed:
        if not rel.lower().endswith(".fdb") or not (bdir / rel).exists():
            continue
        diff, i = [], 0
        with open(root / rel, "rb") as f1, open(bdir / rel, "rb") as f2:
            while len(diff) < limit:
                x, y = f1.read(page), f2.read(page)
                if not x and not y:
                    break
                if x != y:
                    diff.append(i)
                i += 1
        out[rel] = diff
    return out


def explore(a, allow):
    run = Run(a, allow)
    bdir, bfail = a.backup_before_run()
    print(f"백업: {bdir} 실패={bfail}")
    fp_before = a.fingerprint()  # 탐색 시작 직전에 뜬다 (양도박사는 실행만으로도 파일을 쓴다)
    code, reason = 0, None
    try:
        if any("neoTax.fdb" in f for f in bfail):
            raise Abort("neoTax.fdb 백업 실패")
        w, _ = open_root(a, allow)
        run.visit(w.hwnd, [allow["root"]], 0, "window")
    except Abort as e:
        code, reason = 2, str(e)
        print(f"중단: {e}")
    except Exception as e:  # noqa: BLE001
        code, reason = 1, f"{type(e).__name__}: {e}"
        traceback.print_exc()
    # 정리: 처음 보는 모달이 떠 있으면 그대로 둔다
    if not run.unknown_modal:
        for h in a.screens():
            if h != a.main_hwnd and h not in run.start_screens:
                a.close_screen(h)
    diff = a.diff_fingerprint(fp_before, a.fingerprint())
    blocks = fdb_blocks(a.root, bdir, diff["content"])
    summary = {"screens": run.nscreens, "presses": run.presses, "unreviewed": run.unreviewed,
               "errors": run.errors, "abort": reason, "exit_code": code, "externals": run.externals,
               "fingerprint_diff": diff, "fdb_changed_blocks": blocks, "backup": str(bdir), "backup_failed": bfail,
               "elapsed_sec": round(time.time() - run.t0, 1), "remaining_screens": a.screens()}
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"run_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "fingerprint_diff"}, ensure_ascii=False))
    print("지문:", diff)
    print(f"요약: {out}")
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="루트 화면 버튼 분류만 출력")
    args = ap.parse_args()

    ok, why = appmod.available()
    if not ok:
        print(f"{why} — 종료 (Windows + pywinauto 필요)")
        return 0
    a = appmod.App()
    a.attach()
    allow = load_allow()
    try:
        return dry_run(a, allow) if args.dry_run else explore(a, allow)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
