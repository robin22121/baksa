"""케이스 입력 도구 (C000 1단계 W2): 단계 파일(yaml)에 적힌 동작만 눌러 입력한다.

단계 동작: press · radio · text · combo · check_combo · read · capture · verify_grid.
규칙은 docs/work-plans/2026-10-22-C000-양도인등록.md §2. 탐색기(explore.py)와 달리 쓰기 버튼을 누를 수 있으므로
단계 파일에 있는 것만 누르고, 단계 파일에 없는 모달이 뜨면 아무것도 누르지 않고 캡처 후 중단한다.

--dry-run: 값을 넣지 않고 칸·라디오·콤보·버튼을 찾기만 해 표로 출력한다. 단계 파일의 `등록`·`저장`·`취소` 등은 누르지 않는다.
           칸이 안 보이면 `1.양도인등록` 버튼만 1회 누른다(화면 이동, 읽기).
실행: backup_before_run → 백업 헤더 확인 → 단계 → 지문 + fdb 페이지 비교 → cases/basic/<케이스>.run_<시각>.json
종료 코드: 정상 0, 중단(fail/abort) 2, 예외 1.
"""
import argparse
import ctypes
import datetime
import json
import re
import sys
import time
import traceback
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import app as appmod  # noqa: E402
import fake_rrn  # noqa: E402
import yaml  # noqa: E402

ROOT = appmod.ROOT
SCREENS = ROOT / "docs" / "screens"
CASES = ROOT / "cases" / "basic"
ACTIONS = ("press", "radio", "text", "combo", "check_combo", "read", "capture", "verify_grid")
OP_TIMEOUT = 40  # uia 한 번의 조회·조작 상한(초)
norm = appmod.norm


class Stop(Exception):
    """단계 하나의 비정상 결과. status: fail | abort."""

    def __init__(self, status, detail):
        super().__init__(detail)
        self.status, self.detail = status, detail


# ---------------------------------------------------------------- uia 조작 (모두 worker 스레드 안에서 실행)

def clean_title(t):
    return t.split("▶")[0].strip()


def find_el(root, auto_id, ctype=None):
    for c in root.descendants():
        e = c.element_info
        if e.automation_id == auto_id and (ctype is None or e.control_type == ctype):
            return c
    return None


def op_inventory(hwnd):
    """창 안 컨트롤 목록 [(type, name, auto_id, enabled)] (일반 값만 돌려준다)."""
    out = []
    for c in appmod.wrap(hwnd).descendants():
        e = c.element_info
        out.append((e.control_type, e.name or "", e.automation_id or "", bool(e.enabled)))
    return out


def btn_states_from(inv):
    d = {}
    for t, name, _id, en in inv:
        if t == "Button" and name.strip():
            d.setdefault(norm(name), []).append(en)
    return d


def _value_cands(el):
    """칸의 값 후보: ValuePattern, window_text, 자식 Edit의 값 (이름은 라벨이라 쓰지 않는다)."""
    out = []
    try:
        out.append(el.iface_value.CurrentValue)
    except Exception:  # noqa: BLE001
        pass
    try:
        out.append(el.window_text())
    except Exception:  # noqa: BLE001
        pass
    if not any(x for x in out):
        try:
            for ch in el.descendants(control_type="Edit"):
                try:
                    out.append(ch.iface_value.CurrentValue)
                except Exception:  # noqa: BLE001
                    out.append(ch.window_text())
        except Exception:  # noqa: BLE001
            pass
    return [str(x) for x in out if x not in (None, "")]


def _combo_cands(el):
    c = _value_cands(el)
    try:
        c.append(el.element_info.name or "")
    except Exception:  # noqa: BLE001
        pass
    try:
        c.append(el.selected_text())
    except Exception:  # noqa: BLE001
        pass
    return [x for x in c if x]


def same_text(want, got_list):
    """글자 칸: 공백을 지운 값이 같다. 숫자 13자리면 숫자만 뽑아 비교(주민번호)."""
    if re.fullmatch(r"\d{13}", want):
        return any(re.sub(r"\D", "", g) == want for g in got_list)
    return any(re.sub(r"\s+", "", g) == re.sub(r"\s+", "", want) for g in got_list)


def same_combo(want, got_list):
    return any(norm(want) in norm(g) for g in got_list)


def fg_ensure(hwnd):
    """대상 창을 앞으로 가져오고 전경 HWND가 그 창인지 확인(최대 3회). (일치 여부, 관찰한 전경 hwnd들)."""
    seen = []
    for _ in range(3):
        try:
            appmod.wrap(hwnd).set_focus()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.25)
        seen.append(appmod.foreground_hwnd())
        if seen[-1] == hwnd:
            return True, seen
    return False, seen


def set_clipboard(text):
    """유니코드 문자열을 클립보드에 둔다(붙여넣기용)."""
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    u32.OpenClipboard.argtypes = [ctypes.c_void_p]
    data = (text + "\0").encode("utf-16-le")
    h = k32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
    p = k32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    k32.GlobalUnlock(h)
    for _ in range(10):
        if u32.OpenClipboard(None):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("클립보드를 열 수 없음")
    try:
        u32.EmptyClipboard()
        u32.SetClipboardData(13, h)  # CF_UNICODETEXT
    finally:
        u32.CloseClipboard()


def esc_keys(text):
    """send_keys 특수문자 이스케이프."""
    return "".join("{" + ch + "}" if ch in "{}+^%~()[]" else ch for ch in text)


def op_input(hwnd, auto_id, ctype, want, kind):
    """칸 하나에 값을 넣고 Tab으로 확정한 뒤 다시 읽는다.
    시도 순서: ① ValuePattern 설정 ② Ctrl+A 후 영문은 type_keys, 한글 등은 클립보드 붙여넣기. 매 시도 직전에 전경 확인."""
    from pywinauto.keyboard import send_keys
    el = find_el(appmod.wrap(hwnd), auto_id, ctype)
    if el is None:
        return {"found": False}
    log = {"found": True, "enabled": bool(el.element_info.enabled), "attempts": [], "foreground": [], "ok": False}
    if not log["enabled"]:
        return log
    cands = _combo_cands if kind == "combo" else _value_cands
    same = same_combo if kind == "combo" else same_text
    log["before"] = cands(el)

    for method in ("set_value", "type" if want.isascii() else "paste"):
        okfg, seen = fg_ensure(hwnd)
        log["foreground"].append({"before": method, "ok": okfg, "hwnds": seen})
        if not okfg:
            return log
        att = {"method": method}
        try:
            try:
                el.set_focus()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.15)
            if method == "set_value":
                el.iface_value.SetValue(want)
            else:
                send_keys("^a")
                time.sleep(0.1)
                if method == "type":
                    send_keys(esc_keys(want), with_spaces=True, pause=0.03)
                else:
                    set_clipboard(want)
                    send_keys("^v")
            time.sleep(0.25)
            send_keys("{TAB}")  # Tab으로 확정. Enter는 쓰지 않는다.
            time.sleep(0.4)
            att["read"] = cands(el)
            att["match"] = same(want, att["read"])
        except Exception as e:  # noqa: BLE001
            att["error"] = f"{type(e).__name__}: {e}"
            att["match"] = False
        log["attempts"].append(att)
        if att["match"]:
            log["ok"], log["method"], log["read"] = True, method, att["read"]
            return log
        # 모달이 떴을 수 있으니 다음 시도 전에 중단 판단은 호출자가 한다(전경 확인이 실패하면 여기서 멈춘다)
    log["read"] = log["attempts"][-1].get("read", []) if log["attempts"] else []
    return log


def op_read(hwnd, auto_id, ctype=None, combo=False):
    el = find_el(appmod.wrap(hwnd), auto_id, ctype)
    if el is None:
        return {"found": False}
    return {"found": True, "enabled": bool(el.element_info.enabled),
            "values": (_combo_cands if combo else _value_cands)(el)}


def _is_selected(rb):
    try:
        return bool(rb.iface_selection_item.CurrentIsSelected)
    except Exception:  # noqa: BLE001
        pass
    try:
        return rb.get_toggle_state() == 1
    except Exception:  # noqa: BLE001
        return None


def op_radio(hwnd, group, value, act=True):
    """group(auto_id) 아래에서 이름이 value인 RadioButton을 찾아 고른다(act=False면 찾기만)."""
    root = appmod.wrap(hwnd)
    g = find_el(root, group)
    if g is None:
        return {"found": False, "why": "그룹 없음"}
    rbs = [c for c in g.descendants(control_type="RadioButton")]
    if not rbs:  # 형제로 나열되는 경우: 그룹 다음에 이어지는 RadioButton들
        seen, rbs = False, []
        for c in root.descendants():
            e = c.element_info
            if not seen:
                seen = e.automation_id == group
            elif e.control_type == "RadioButton":
                rbs.append(c)
            elif rbs and e.control_type != "Text":
                break
    names = [r.element_info.name for r in rbs]
    tgt = next((r for r in rbs if norm(r.element_info.name) == norm(value)), None)
    if tgt is None:
        return {"found": False, "why": f"항목 없음: {names}"}
    log = {"found": True, "enabled": bool(tgt.element_info.enabled), "items": names}
    if not act:
        return log
    if not log["enabled"]:
        return log
    log["method"] = "select"
    try:
        tgt.iface_selection_item.Select()
    except Exception as e:  # noqa: BLE001
        log["select_error"] = f"{type(e).__name__}: {e}"
    time.sleep(0.4)
    sel = _is_selected(tgt)
    if not sel:
        r = tgt.element_info.rectangle
        h = appmod.post_click_at(hwnd, (r.left + r.right) // 2, (r.top + r.bottom) // 2)
        log["method"] = f"select→postclick({h})"
        time.sleep(0.5)
        sel = _is_selected(tgt)
    log["selected"] = sel
    log["ok"] = bool(sel)
    return log


def op_click_button(hwnd, name):
    """UIA 좌표로 버튼 중앙에 PostMessage 클릭(win32 텍스트로 못 찾았을 때의 대체)."""
    for c in appmod.wrap(hwnd).descendants(control_type="Button"):
        if norm(c.element_info.name) == norm(name):
            r = c.element_info.rectangle
            return appmod.post_click_at(hwnd, (r.left + r.right) // 2, (r.top + r.bottom) // 2)
    return 0


def _cell_value(c):
    try:
        return str(c.iface_value.CurrentValue or "")
    except Exception:  # noqa: BLE001
        pass
    try:
        return str(c.legacy_properties().get("Value") or "")
    except Exception:  # noqa: BLE001
        return ""


def op_grid(hwnd, auto_id, contains, column=None):
    """DevExpress 그리드: Table > Custom 'Row n' > DataItem '<열> row n'. 셀 값은 ValuePattern.
    contains를 값에 포함한 행 수(matched)와 전체 행 수(rows), 행별 {열: 값}(최대 20행)을 돌려준다."""
    g = find_el(appmod.wrap(hwnd), auto_id)
    if g is None:
        return {"found": False}
    rows = []
    for r in g.descendants(control_type="Custom"):
        if not re.fullmatch(r"Row \d+", (r.element_info.name or "").strip()):
            continue
        cells = {}
        for c in r.descendants(control_type="DataItem"):
            col = re.sub(r"\s+row\s+\d+\s*$", "", c.element_info.name or "")
            cells[col] = _cell_value(c)
        rows.append(cells)
    w = norm(contains)
    hit = [r for r in rows if any(w in norm(v) for k, v in r.items() if column is None or norm(k) == norm(column))]
    return {"found": True, "rows": len(rows), "matched": len(hit), "row_values": rows[:20], "column": column}


# ---------------------------------------------------------------- 단계 파일

def subst(obj, vars_):
    if isinstance(obj, str):
        for k, v in vars_.items():
            obj = obj.replace("{" + k + "}", str(v))
        return obj
    if isinstance(obj, list):
        return [subst(x, vars_) for x in obj]
    if isinstance(obj, dict):
        return {k: subst(v, vars_) for k, v in obj.items()}
    return obj


def load_steps(path):
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    vars_ = {}
    for k, v in (d.get("vars") or {}).items():
        if isinstance(v, dict) and "fake_rrn" in v:
            a = v["fake_rrn"] or {}
            vars_[k] = fake_rrn.make(a.get("birth", "1985-05-05"), a.get("sex", "M"))  # 숫자만 13자리
        else:
            vars_[k] = v
    steps = subst(d.get("steps") or [], vars_)
    for i, s in enumerate(steps, 1):
        keys = [k for k in s if k in ACTIONS]
        if len(keys) != 1:
            raise ValueError(f"단계 {i}: 동작 키가 정확히 1개여야 함 {list(s)}")
    return d.get("window", ""), vars_, steps


def action_of(step):
    return next(k for k in step if k in ACTIONS)


def case_id(path):
    return Path(path).name.split(".")[0]


def run_base(path):
    n = Path(path).name
    return n[:-len(".steps.yaml")] if n.endswith(".steps.yaml") else Path(path).stem


def find_target(a, name):
    for w in a.screens_info():
        if w.hwnd != a.main_hwnd and norm(clean_title(w.title)) == norm(name):
            return w
    return None


def guard(fn, sec=OP_TIMEOUT):
    return appmod.call_with_timeout(fn, sec)


# ---------------------------------------------------------------- dry-run

def find_status(found, enabled=True):
    if not found:
        return "못 찾음"
    return "찾음" if enabled else "찾음(비활성)"


def dry_run(a, window, steps):
    w = find_target(a, window)
    if not w:
        print(f"창 {window!r}이(가) 열려 있지 않음 — dry-run은 창을 열지 않는다")
        return 2
    hwnd = w.hwnd
    print(f"대상 창: {clean_title(w.title)!r} hwnd={hwnd}")
    if a.modals():
        print(f"열려 있는 모달 {a.modals()} — 먼저 닫아야 함")
        return 2
    inv = guard(lambda: op_inventory(hwnd))
    ids = {i: (t, n, en) for t, n, i, en in inv if i}
    need = []
    for s in steps:
        k = action_of(s)
        if k in ("text", "combo", "check_combo", "verify_grid"):
            need.append(s[k]["id"])
        elif k == "radio":
            need.append(s[k]["group"])
        elif k == "read":
            need.extend(s[k])
    pressed = None
    if any(i not in ids for i in need):
        nav = next((norm(s["press"]) for s in steps if action_of(s) == "press" and "양도인등록" in norm(s["press"])), None)
        if nav and any(btn_states_from(inv).get(nav, [False])) and not a.is_forbidden(nav):
            print(f"칸이 보이지 않아 {nav!r} 버튼을 1회 누른다(화면 이동, 읽기)")
            if not a.press(hwnd, nav):
                guard(lambda: op_click_button(hwnd, nav))
            pressed = nav
            time.sleep(1.5)
            if a.modals():
                print(f"누른 뒤 모달이 떴다: {[a.modal_key(m) for m in a.modals_info()]} — 아무것도 누르지 않고 중단")
                return 2
            inv = guard(lambda: op_inventory(hwnd))
            ids = {i: (t, n, en) for t, n, i, en in inv if i}
    btns = btn_states_from(inv)

    rows = []

    def add(i, act, target, st):
        rows.append((i, act, target, st))

    for i, s in enumerate(steps, 1):
        k = action_of(s)
        if k == "press":
            nm = s["press"]
            st = btns.get(norm(nm))
            add(i, "press", nm, find_status(st is not None, bool(st) and any(st)))
            for key in ("expect_enabled", "expect_disabled"):
                for b in s.get(key, []) or []:
                    st = btns.get(norm(b))
                    add(i, key, b, find_status(st is not None, bool(st) and any(st)))
        elif k in ("text", "combo", "check_combo"):
            sp = s[k]
            ct = "Edit" if k == "text" else "ComboBox"
            t = ids.get(sp["id"])
            add(i, k, f"{sp['id']} ({ct})", find_status(bool(t) and t[0] == ct, bool(t) and t[2]))
        elif k == "read":
            for x in s["read"]:
                t = ids.get(x)
                add(i, "read", x, find_status(bool(t), bool(t) and t[2]))
        elif k == "verify_grid":
            t = ids.get(s[k]["id"])
            add(i, "verify_grid", s[k]["id"], find_status(bool(t), bool(t) and t[2]))
        elif k == "radio":
            sp = s[k]
            r = guard(lambda sp=sp: op_radio(hwnd, sp["group"], sp["value"], act=False))
            add(i, "radio", f"{sp['group']}/{sp['value']}" + ("" if r["found"] else f" [{r.get('why')}]"),
                find_status(r["found"], r.get("enabled", False)))
    print(f"\n{'단계':>3}  {'동작':<14} {'대상':<44} 결과")
    for i, act, target, st in rows:
        print(f"{i:>3}  {act:<14} {target:<44} {st}")
    miss = sum(1 for r in rows if r[3] == "못 찾음")
    off = sum(1 for r in rows if r[3] == "찾음(비활성)")
    print(f"\n합계: 찾음 {len(rows) - miss - off}, 찾음(비활성) {off}, 못 찾음 {miss}"
          + (f"  (이번에 {pressed!r} 1회 누름)" if pressed else "  (아무것도 누르지 않음)"))
    return 0 if miss == 0 else 2


# ---------------------------------------------------------------- 실행

class Runner:
    def __init__(self, a, hwnd, case):
        self.a, self.hwnd, self.case = a, hwnd, case
        self.start_screens = set(a.screens())
        self.results = []
        self.reads = {}
        self.i = 0

    # -- 공통
    def snap(self):
        return set(self.a.screens()), set(self.a.modals()), set(self.a.externals())

    def inv(self):
        return guard(lambda: op_inventory(self.hwnd))

    def btn_states(self):
        return btn_states_from(self.inv())

    def shot(self, label):
        path = SCREENS / f"{self.case}_{self.i:02d}_{label}.png"
        return self.a.capture(self.hwnd, path), str(path.relative_to(ROOT)).replace("\\", "/")

    def shot_modal(self, w, label):
        path = SCREENS / f"{self.case}_{self.i:02d}_{label}.png"
        return self.a.capture(w.hwnd, path), str(path.relative_to(ROOT)).replace("\\", "/")

    def handle_modal(self, w, step, rec):
        key = self.a.modal_key(w)
        mm = {norm(k): ([norm(x) for x in v] if isinstance(v, list) else [norm(v)])
              for k, v in (step.get("modals") or {}).items()}
        item = {"key": key, "title": w.title, "msg": w.msg}
        rec.setdefault("modals", []).append(item)
        if key not in mm:
            item["handled"] = False
            item["capture"] = self.shot_modal(w, "modal_unknown")
            raise Stop("abort", f"처음 보는 모달 {key!r} — 아무것도 누르지 않음. 단계 파일 modals에 추가 필요")
        for b in mm[key]:
            if not self.a.press(w.hwnd, b):
                item["capture"] = self.shot_modal(w, "modal_nobutton")
                raise Stop("abort", f"모달 {key!r}에서 버튼 {b!r}을 누를 수 없음")
            item.setdefault("pressed", []).append(b)
        gone = appmod.wait_for(lambda: w.hwnd not in self.a.modals(), 4)
        item["handled"] = bool(gone)
        if not gone:
            raise Stop("abort", f"모달 {key!r}이(가) 닫히지 않음")

    def settle(self, step, rec, before, base_wait=0.8):
        """누르거나 입력한 뒤: 새 모달은 단계 파일 규칙대로 처리, 새 화면·외부 창은 중단."""
        appmod.wait_for(lambda: set(self.a.modals()) - before[1] or set(self.a.screens()) - before[0], 2.0, 0.25)
        time.sleep(base_wait)
        for _ in range(5):
            new = [w for w in self.a.modals_info() if w.hwnd not in before[1]]
            if not new:
                break
            for w in new:
                self.handle_modal(w, step, rec)
            time.sleep(0.6)
        new_s = set(self.a.screens()) - before[0]
        smap = {norm(k): norm(v) for k, v in (step.get("screens") or {}).items()}
        for h in sorted(new_s):
            w = next((x for x in self.a.screens_info() if x.hwnd == h), None)
            tk = norm(clean_title(w.title)) if w else ""
            if tk not in smap:
                continue
            item = {"title": w.title, "hwnd": h, "pressed": smap[tk]}
            rec.setdefault("handled_screens", []).append(item)
            cp = SCREENS / f"{self.case}_{self.i:02d}_screen_{len(rec['handled_screens'])}.png"
            item["capture_method"] = self.a.capture(h, cp)
            item["capture"] = str(cp.relative_to(ROOT)).replace("\\", "/")
            if not self.a.press(h, smap[tk]):
                raise Stop("abort", f"화면 {w.title!r}에서 버튼 {smap[tk]!r}을 누를 수 없음")
            if not appmod.wait_for(lambda h=h: h not in self.a.screens(), 5.0):
                raise Stop("fail", f"화면 {w.title!r}이(가) 5초 안에 닫히지 않음")
            time.sleep(0.5)
            new_s.discard(h)
        if new_s:
            rec["new_screens"] = sorted(new_s)
            self.shot("new_screen")
            raise Stop("abort", f"새 화면이 떴다 {sorted(new_s)} — 단계 파일에 반영 필요")
        new_e = set(self.a.externals()) - before[2]
        if new_e:
            rec["new_externals"] = [list(self.a.externals().get(h, ("", ""))) for h in new_e]
            raise Stop("abort", f"외부 창이 떴다 {rec['new_externals']}")

    # -- 동작
    def do_press(self, step, rec):
        name = step["press"]
        if self.a.is_forbidden(name):
            raise Stop("abort", f"금지 목록에 걸리는 버튼 {name!r}")
        st = self.btn_states().get(norm(name))
        if st is None:
            raise Stop("fail", f"버튼 없음 {name!r}")
        if not any(st):
            raise Stop("fail", f"버튼 비활성 {name!r}")
        before = self.snap()
        how = "postmessage"
        if not self.a.press(self.hwnd, name):
            how = "uia좌표"
            if not guard(lambda: op_click_button(self.hwnd, name)):
                raise Stop("fail", f"버튼을 누를 수 없음 {name!r}")
        rec["how"] = how
        self.settle(step, rec, before)
        exp_en = step.get("expect_enabled") or []
        exp_dis = step.get("expect_disabled") or []
        if exp_en or exp_dis:
            last = {}

            def ok():
                last.update(self.btn_states())
                return (all(any(last.get(norm(b), [False])) for b in exp_en)
                        and all(norm(b) in last and not any(last[norm(b)]) for b in exp_dis))

            good = appmod.wait_for(ok, 6.0, 0.7)
            rec["states"] = {b: last.get(norm(b)) for b in exp_en + exp_dis}
            if not good:
                raise Stop("fail", f"기대 상태와 다름 enabled={exp_en} disabled={exp_dis} 실제={rec['states']}")

    def _input(self, step, rec, kind):
        sp = step[kind]
        want = str(sp["value"])
        ctype = "Edit" if kind == "text" else "ComboBox"
        title0 = clean_title(next((w.title for w in self.a.screens_info() if w.hwnd == self.hwnd), ""))
        save0 = self.btn_states().get(norm("저장")) if kind == "combo" else None
        before = self.snap()
        res = guard(lambda: op_input(self.hwnd, sp["id"], ctype, want, kind))
        rec["result"] = res
        rec["want"] = want
        self.settle(step, rec, before, base_wait=0.3)  # 모달이 먼저다
        if not res["found"]:
            raise Stop("fail", f"칸을 못 찾음 {sp['id']}")
        if not res["enabled"]:
            raise Stop("fail", f"칸이 비활성 {sp['id']}")
        if res["foreground"] and not res["foreground"][-1]["ok"]:
            raise Stop("fail", f"전경 창이 대상 창이 아님 {res['foreground'][-1]['hwnds']} (대상 {self.hwnd})")
        if not res["ok"]:
            raise Stop("fail", f"값이 들어가지 않음 {sp['id']} 원하는={want!r} 읽은={res.get('read')}")
        if kind == "combo":
            title1 = clean_title(next((w.title for w in self.a.screens_info() if w.hwnd == self.hwnd), ""))
            save1 = self.btn_states().get(norm("저장"))
            rec["title_same"], rec["save_same"] = title0 == title1, save0 == save1
            if title0 != title1 or save0 != save1:
                self.shot("combo_changed")
                raise Stop("fail", f"콤보 뒤 창 제목/저장 버튼 상태가 달라짐 {title0!r}→{title1!r} 저장 {save0}→{save1}")

    def do_text(self, step, rec):
        self._input(step, rec, "text")

    def do_combo(self, step, rec):
        self._input(step, rec, "combo")

    def do_check_combo(self, step, rec):
        sp = step["check_combo"]
        res = guard(lambda: op_read(self.hwnd, sp["id"], "ComboBox", combo=True))
        rec["result"] = res
        if not res["found"]:
            raise Stop("fail", f"콤보를 못 찾음 {sp['id']}")
        if not same_combo(str(sp["value"]), res["values"]):
            raise Stop("fail", f"콤보 값이 다름 원하는={sp['value']!r} 읽은={res['values']}")

    def do_radio(self, step, rec):
        sp = step["radio"]
        before = self.snap()
        res = guard(lambda: op_radio(self.hwnd, sp["group"], sp["value"]))
        rec["result"] = res
        self.settle(step, rec, before, base_wait=0.2)
        if not res["found"]:
            raise Stop("fail", f"라디오를 못 찾음 {sp['group']}/{sp['value']}: {res.get('why')}")
        if not res["enabled"]:
            raise Stop("fail", f"라디오 비활성 {sp['group']}/{sp['value']}")
        if not res.get("ok"):
            raise Stop("fail", f"라디오가 선택되지 않음 {sp['group']}/{sp['value']} ({res.get('method')})")

    def do_read(self, step, rec):
        vals = {}
        for x in step["read"]:
            r = guard(lambda x=x: op_read(self.hwnd, x))
            if not r["found"]:
                raise Stop("fail", f"칸을 못 찾음 {x}")
            vals[x] = r["values"]
        rec["values"] = vals
        self.reads.update(vals)

    def do_capture(self, step, rec):
        status, rel = self.shot(step["capture"])
        rec["capture"], rec["capture_method"] = rel, status
        if status == "failed":
            raise Stop("fail", "캡처 실패")

    def do_verify_grid(self, step, rec):
        sp = step["verify_grid"]
        want = sp.get("count")
        last = {}

        def ok():
            last.clear()
            last.update(guard(lambda: op_grid(self.hwnd, sp["id"], sp["contains"], sp.get("column"))))
            return last["found"] and (last["matched"] == want if want is not None else last["matched"] >= 1)

        appmod.wait_for(ok, 5.0, 1.0)
        rec["result"] = dict(last)
        if not last.get("found"):
            raise Stop("fail", f"그리드를 못 찾음 {sp['id']}")
        if not ok():
            raise Stop("fail", f"일치 행 수 {last.get('matched')} != {want} (contains={sp['contains']!r}, 전체 행 {last.get('rows')}) {last.get('row_values')}")

    def run(self, steps):
        """단계를 순서대로 실행. fail/abort는 즉시 멈추고, 그 이유(문자열)를 돌려준다. 예외는 기록 후 다시 던진다."""
        for self.i, step in enumerate(steps, 1):
            act = action_of(step)
            rec = {"i": self.i, "action": act, "spec": json.loads(json.dumps(step, ensure_ascii=False, default=str)),
                   "t": datetime.datetime.now().isoformat(timespec="seconds")}
            self.results.append(rec)
            print(f"[{self.i:02d}] {act}: {json.dumps(step[act], ensure_ascii=False, default=str)}", flush=True)
            try:
                getattr(self, "do_" + act)(step, rec)
                rec["status"] = "ok"
                print("     ok", flush=True)
            except Stop as s:
                rec["status"], rec["detail"] = s.status, s.detail
                print(f"     {s.status}: {s.detail}", flush=True)
                return f"단계 {self.i} {act} {s.status}: {s.detail}"
            except Exception as e:  # noqa: BLE001
                rec["status"], rec["detail"] = "error", f"{type(e).__name__}: {e}"
                rec["trace"] = traceback.format_exc()
                raise
        return None


def fdb_verdict(pages, fp_diff):
    out = {"added": fp_diff["added"], "removed": fp_diff["removed"], "files": {}}
    for rel, r in pages.items():
        kinds = set(r["by_type"])
        out["files"][rel] = {"changed_total": r["changed_total"], "by_type": r["by_type"],
                             "only_header_tip": kinds <= {"header", "TIP"}, "data_type_changed": r["data_type_changed"],
                             "size_same": r["size_same"]}
    tax = out["files"].get("Data/neoTax.fdb")
    out["neoTax_data_changed"] = bool(tax and tax["data_type_changed"] > 0)
    out["others_only_header_tip"] = all(v["only_header_tip"] for k, v in out["files"].items() if k != "Data/neoTax.fdb")
    return out


def execute(a, steps_path, window, vars_, steps):
    case = case_id(steps_path)
    base = run_base(steps_path)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    prior = len(list(CASES.glob(f"{base}.run_*.json")))
    rec = {"steps_file": str(Path(steps_path)), "case": case, "started": datetime.datetime.now().isoformat(timespec="seconds"),
           "window": window, "vars": vars_, "prior_runs_same_steps": prior}
    print(f"같은 단계 파일의 이전 실행 기록 {prior}개 (재실행 상한 3회)")
    code, reason = 0, None
    out = CASES / f"{base}.run_{ts}.json"
    runner = None
    try:
        w = find_target(a, window)
        if not w:
            raise Stop("abort", f"창 {window!r}이(가) 열려 있지 않음")
        if a.modals():
            raise Stop("abort", f"실행 전에 모달이 열려 있음 {a.modals()}")
        rec["hwnd"] = w.hwnd
        bdir, bfail = a.backup_before_run()
        rec["backup"], rec["backup_failed"] = str(bdir), bfail
        print(f"백업: {bdir} 실패={bfail}")
        if any("neoTax.fdb" in f for f in bfail):
            raise Stop("abort", "neoTax.fdb 백업 실패")
        probs = a.check_backup(bdir)
        rec["backup_header_problems"] = probs
        if probs:
            raise Stop("abort", f"백업 헤더 불일치 {probs}")
        print("백업 헤더(페이지 크기·수·파일 크기) 원본과 일치")
        fp_before = a.fingerprint()
        runner = Runner(a, w.hwnd, case)
        try:
            reason = runner.run(steps)
        finally:
            rec["results"], rec["reads"] = runner.results, runner.reads
        if reason:
            code = 2
    except Stop as s:
        code, reason = 2, f"{s.status}: {s.detail}"
        print(f"중단: {reason}")
    except Exception as e:  # noqa: BLE001
        code, reason = 1, f"{type(e).__name__}: {e}"
        traceback.print_exc()
    if "backup" in rec and "backup_header_problems" in rec and not rec["backup_header_problems"]:
        try:
            diff = a.diff_fingerprint(fp_before, a.fingerprint())
            pages = a.fdb_compare_all(Path(rec["backup"]))
            rec["fingerprint_diff"], rec["fdb_pages"] = diff, pages
            rec["fdb_verdict"] = fdb_verdict(pages, diff)
            print("지문:", {k: (v if k != "mtime_only" else f"{len(v)}개") for k, v in diff.items()})
            for rel, r in pages.items():
                print(f"fdb {rel}: 페이지 크기 {r['page_size']} 페이지 {r['pages_old']}→{r['pages_new']} 바뀐 {r['changed_total']} 타입별 {r['by_type']}")
            v = rec["fdb_verdict"]
            print(f"neoTax 데이터 페이지(타입 4~7) 변경: {v['neoTax_data_changed']}, 다른 fdb는 헤더·TIP만: {v['others_only_header_tip']}, "
                  f"added/removed: {len(diff['added'])}/{len(diff['removed'])}")
        except Exception as e:  # noqa: BLE001
            rec["compare_error"] = f"{type(e).__name__}: {e}"
            if code == 0:
                code = 1
            traceback.print_exc()
    rec.update({"abort": reason, "exit_code": code, "finished": datetime.datetime.now().isoformat(timespec="seconds"),
                "remaining_screens": a.screens(), "remaining_modals": a.modals()})
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"실행 기록: {out}")
    return code


def main():
    ap = argparse.ArgumentParser(description="케이스 입력 도구 (단계 파일 실행기)")
    ap.add_argument("--steps", required=True, help="단계 파일(yaml)")
    ap.add_argument("--dry-run", action="store_true", help="값을 넣지 않고 칸·버튼만 찾아 표로 출력")
    args = ap.parse_args()
    ok, why = appmod.available()
    if not ok:
        print(f"{why} — 종료 (Windows + pywinauto 필요)")
        return 0
    try:
        window, vars_, steps = load_steps(args.steps)
        a = appmod.App()
        a.attach()
        if args.dry_run:
            return dry_run(a, window, steps)
        return execute(a, args.steps, window, vars_, steps)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
