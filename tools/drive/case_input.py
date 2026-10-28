"""케이스 입력 도구 (C000 1단계 W2): 단계 파일(yaml)에 적힌 동작만 눌러 입력한다.

단계 동작: press · radio · text · combo · check_combo · read · capture · verify_grid.
규칙은 docs/work-plans/2026-10-22-C000-양도인등록.md §2. 탐색기(explore.py)와 달리 쓰기 버튼을 누를 수 있으므로
단계 파일에 있는 것만 누르고, 단계 파일에 없는 모달이 뜨면 아무것도 누르지 않고 캡처 후 중단한다.

--dry-run: 값을 넣지 않고 칸·라디오·콤보·버튼을 찾기만 해 표로 출력한다. 단계 파일의 `등록`·`저장`·`취소` 등은 누르지 않는다.
           칸이 안 보이면 `1.양도인등록` 버튼만 1회 누른다(화면 이동, 읽기).
실행: backup_before_run → 백업 헤더 확인 → 단계 → 지문 + fdb 페이지 비교 → cases/basic/<케이스>.run_<시각>.json
단계마다 시작 시 열려 있는 모달(이전 단계 뒤늦게 뜬 것)은 단계 modals 규칙으로 처리(rec.modals_at_start), 없으면 캡처 후 중단.
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
ACTIONS = ("press", "radio", "text", "combo", "check_combo", "read", "capture", "verify_grid",
           "window", "radio_id", "tab", "grid_cell", "close", "press_id", "click_id")
OP_TIMEOUT = 40  # uia 한 번의 조회·조작 상한(초)
norm = appmod.norm


class Stop(Exception):
    """단계 하나의 비정상 결과. status: fail | abort."""

    def __init__(self, status, detail):
        super().__init__(detail)
        self.status, self.detail = status, detail


# ---------------------------------------------------------------- uia 조작 (모두 worker 스레드 안에서 실행)

def _modal_match(mapkey, key):
    """모달 키 비교: 제목·문구 부분이 '*부분*'이면 포함 여부, '*'만 있으면 전부, 그 밖은 정확히 같음."""
    if "|" not in mapkey or "|" not in key:
        return False
    mt, mm = mapkey.split("|", 1)
    kt, km = key.split("|", 1)

    def ok(m, k):
        if m == "*":
            return True
        if len(m) > 2 and m.startswith("*") and m.endswith("*"):
            return m[1:-1] in k
        return m == k

    return ok(mt, kt) and ok(mm, km)


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


def _legacy_value(el):
    try:
        return el.legacy_properties().get("Value") or ""
    except Exception:  # noqa: BLE001
        return ""


def _value_cands(el, use_name=False):
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
    out.append(_legacy_value(el))
    if use_name:  # Pane 등 값 패턴이 없는 칸: 이름이 값을 따라 바뀌는지 보기 위해
        out.append(el.element_info.name)
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


def date_of(s):
    """'2025-06-30'·'2025년 6월 30일 월요일' 등에서 (연, 월, 일)."""
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def same_text(want, got_list):
    """글자 칸: 공백을 지운 값이 같다. 숫자 13자리면 숫자만 뽑아 비교(주민번호). 날짜는 (연,월,일)로 비교."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", want):
        return any(date_of(g) == date_of(want) for g in got_list)
    if re.fullmatch(r"\d{13}", want):
        return any(re.sub(r"\D", "", g) == want for g in got_list)
    if re.fullmatch(r"[\d,.\-]+", want):  # 금액·날짜: 공백·쉼표 무시
        return any(re.sub(r"[\s,]", "", g) == re.sub(r"[\s,]", "", want) for g in got_list)
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


def op_input(hwnd, auto_id, ctype, want, kind, use_name=False):
    """칸 하나에 값을 넣고 Tab으로 확정한 뒤 다시 읽는다.
    시도 순서: ① ValuePattern 설정 ② Ctrl+A 후 영문은 type_keys, 한글 등은 클립보드 붙여넣기. 매 시도 직전에 전경 확인."""
    from pywinauto.keyboard import send_keys
    el = find_el(appmod.wrap(hwnd), auto_id, ctype)
    if el is None:
        return {"found": False}
    log = {"found": True, "enabled": bool(el.element_info.enabled), "attempts": [], "foreground": [], "ok": False}
    if not log["enabled"]:
        return log
    cands = _combo_cands if kind == "combo" else (lambda e: _value_cands(e, use_name))
    same = same_combo if kind == "combo" else same_text
    log["before"] = cands(el)

    for method in ("set_value", "type" if want.isascii() else "paste", "mouse"):
        okfg, seen = fg_ensure(hwnd)
        log["foreground"].append({"before": method, "ok": okfg, "hwnds": seen})
        if not okfg:
            return log
        att = {"method": method}
        try:
            if method == "mouse":  # 실제 마우스로 칸 중앙을 눌러 편집을 켠 뒤 입력(위 방법이 안 먹는 칸용)
                from pywinauto import mouse
                r = el.element_info.rectangle
                mouse.click(coords=((r.left + r.right) // 2, (r.top + r.bottom) // 2))
                time.sleep(0.4)
                okfg, seen = fg_ensure(hwnd)
                log["foreground"].append({"before": "mouse-input", "ok": okfg, "hwnds": seen})
                if not okfg:
                    return log
            else:
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
                if method in ("type", "mouse"):
                    # 날짜 마스크 칸(____-__-__)은 숫자만 쳐야 하이픈이 자동으로 채워진다
                    keys = re.sub(r"\D", "", want) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", want) and use_name else want
                    send_keys(esc_keys(keys), with_spaces=True, pause=0.03)
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


def _combo_selection_names(el):
    """콤보 SelectionPattern의 선택 항목 이름들. 읽을 수 없으면 None."""
    try:
        arr = el.iface_selection.GetCurrentSelection()
        return [arr.GetElement(i).CurrentName for i in range(arr.Length)]
    except Exception:  # noqa: BLE001
        return None


def _list_items(el, before_handles):
    """펼친 목록의 ListItem: 콤보 자손 → 없으면 새로 생긴 데스크톱 최상위 창의 자손."""
    items = []
    try:
        items = list(el.descendants(control_type="ListItem"))
    except Exception:  # noqa: BLE001
        pass
    if not items:
        try:
            from pywinauto import Desktop
            for w in Desktop(backend="uia").windows():
                if w.handle in before_handles:
                    continue
                items.extend(w.descendants(control_type="ListItem"))
        except Exception:  # noqa: BLE001
            pass
    return items


def op_combo_select(hwnd, auto_id, want):
    """콤보를 펼쳐 목록에서 이름이 같은 항목을 골라 확정한다(글자만 넣으면 선택 항목이 안 바뀌는 DevExpress 콤보용).
    펼치기: ExpandCollapse → 안 되면 오른쪽 끝 버튼 영역 실제 클릭. 고르기: SelectionItem.Select → 안 되면 실제 클릭. Enter는 쓰지 않는다.
    고른 뒤에도 목록이 열려 있으면(펼침 패턴 없는 콤보) 항목 중앙을 실제 클릭해 닫고 log["closed_by"]에 기록, 그래도 열려 있으면 ok=False."""
    from pywinauto import mouse
    el = find_el(appmod.wrap(hwnd), auto_id, "ComboBox")
    if el is None:
        return {"found": False}
    log = {"found": True, "enabled": bool(el.element_info.enabled), "attempts": [], "foreground": [], "ok": False,
           "method": "select"}
    if not log["enabled"]:
        return log
    log["before"] = _combo_cands(el)
    okfg, seen = fg_ensure(hwnd)
    log["foreground"].append({"before": "expand", "ok": okfg, "hwnds": seen})
    if not okfg:
        return log
    try:
        from pywinauto import Desktop
        before_handles = {w.handle for w in Desktop(backend="uia").windows()}
    except Exception:  # noqa: BLE001
        before_handles = set()
    r = el.element_info.rectangle
    try:
        el.iface_expand_collapse.Expand()
        log["expand"] = "pattern"
    except Exception as e:  # noqa: BLE001
        log["expand_error"] = f"{type(e).__name__}: {e}"
        mouse.click(coords=(r.right - 8, (r.top + r.bottom) // 2))
        log["expand"] = "mouse"
    time.sleep(0.6)
    items = _list_items(el, before_handles)
    names = [i.element_info.name for i in items]
    tgt = next((i for i in items if norm(i.element_info.name) == norm(want)), None)
    if tgt is None and log["expand"] == "pattern":  # 펼침 패턴이 겉으로만 성공했을 수 있다: 버튼 영역 클릭 재시도
        mouse.click(coords=(r.right - 8, (r.top + r.bottom) // 2))
        log["expand"] = "pattern→mouse"
        time.sleep(0.6)
        items = _list_items(el, before_handles)
        names = [i.element_info.name for i in items]
        tgt = next((i for i in items if norm(i.element_info.name) == norm(want)), None)
    log["items"] = names
    if tgt is None:
        log["why"] = f"항목 없음: {names}"
        _combo_collapse(el)
        return log
    try:
        tgt.iface_selection_item.Select()
        log["pick"] = "select"
    except Exception as e:  # noqa: BLE001
        log["select_error"] = f"{type(e).__name__}: {e}"
        tr = tgt.element_info.rectangle
        mouse.click(coords=((tr.left + tr.right) // 2, (tr.top + tr.bottom) // 2))
        log["pick"] = "mouse"
    time.sleep(0.5)
    _combo_collapse(el)
    time.sleep(0.4)
    # F7: 펼침 패턴이 없는 콤보(GU 등)는 Select()만으로 목록이 안 닫힌다 → 열려 있으면 항목을 실제 클릭해 닫는다(Esc는 선택을 되돌릴 수 있어 쓰지 않음)
    log["closed_by"] = "select"
    if _list_still_open(el, before_handles, want):
        tr = tgt.element_info.rectangle
        mouse.click(coords=((tr.left + tr.right) // 2, (tr.top + tr.bottom) // 2))
        log["closed_by"] = "mouse_item"
        time.sleep(0.6)
        if _list_still_open(el, before_handles, want):
            log["why"] = "콤보 목록이 닫히지 않음"
            return log
    att = {"method": "select", "read": _combo_cands(el)}
    att["match"] = same_combo(want, att["read"])
    sel = _combo_selection_names(el)
    if sel is None:
        att["selection_unverified"] = True
        log["selection_unverified"] = True
    else:
        att["selection"] = sel
        att["selection_match"] = any(norm(s) == norm(want) for s in sel)
        log["selection"] = sel
    log["attempts"].append(att)
    log["read"] = att["read"]
    log["ok"] = bool(att["match"]) and (sel is None or att["selection_match"])
    return log


def _list_still_open(el, before_handles, want=None):
    """선택 뒤에도 목록 팝업이 남았는지. 실측(2026-10-29): DevExpress 콤보 ListItem은 팝업이 닫혀도 UIA 트리에 남아
    항목 이름으로는 판별할 수 없다. 팝업이 열려 있는 동안에만 새 최상위 창 클래스 "SysShadow"가 보이고(펼치기 전
    before_handles에 없음), 마우스로 항목을 클릭하면 사라진다(Select()만으로는 남는다). want는 호환용으로 쓰지 않는다."""
    try:
        from pywinauto import Desktop
        u32 = ctypes.windll.user32
        return any(w.class_name() == "SysShadow" and w.handle not in before_handles and bool(u32.IsWindowVisible(w.handle))
                   for w in Desktop(backend="uia").windows())
    except Exception:  # noqa: BLE001
        return False


def _combo_collapse(el):
    try:
        el.iface_expand_collapse.Collapse()
    except Exception:  # noqa: BLE001
        pass


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
    if not act or not log["enabled"]:
        return log
    return _select_item(hwnd, tgt, log)


def _select_item(hwnd, tgt, log):
    """SelectionItem.Select → is_selected 확인, 안 되면 PostMessage 클릭 후 다시 확인."""
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
    if not sel:  # F9: 상태 읽기가 늦게 반영되는 경우 → 클릭 없이 최대 2.0초(0.25초 간격) 재읽기
        n = 0
        while not sel and n < 8:
            time.sleep(0.25)
            n += 1
            sel = _is_selected(tgt)
        log["reread"] = n
        log["reread_true"] = bool(sel)
    log["selected"] = sel
    log["ok"] = bool(sel)
    return log


def op_radio_id(hwnd, auto_id):
    """auto_id로 RadioButton을 직접 찾아 고른다."""
    el = find_el(appmod.wrap(hwnd), auto_id, "RadioButton")
    if el is None:
        return {"found": False, "why": "auto_id 없음"}
    log = {"found": True, "enabled": bool(el.element_info.enabled), "name": el.element_info.name}
    if not log["enabled"]:
        return log
    return _select_item(hwnd, el, log)


def _dataitems(root):
    """DataItem 전체 → [(열이름, 레코드번호, 요소)]. 이름 형식 '<열> row N'."""
    out = []
    for c in root.descendants(control_type="DataItem"):
        m = re.fullmatch(r"(.*?)\s+row\s+(\d+)\s*", c.element_info.name or "")
        if m:
            out.append((m.group(1), int(m.group(2)), c))
    return out


def op_tab(hwnd, name):
    """TabItem(이름 norm 일치)을 고르고(안 되면 PostMessage 클릭) 1.5초 기다린 뒤,
    창 안 DataItem(세로형 그리드 행)의 {열: 값}(레코드 0)을 기록한다."""
    root = appmod.wrap(hwnd)
    tabs = list(root.descendants(control_type="TabItem"))
    names = [c.element_info.name for c in tabs]
    tgt = next((c for c in tabs if norm(c.element_info.name) == norm(name)), None)
    if tgt is None:
        return {"found": False, "tabs": names}
    log = {"found": True, "tabs": names}
    _select_item(hwnd, tgt, log)
    log["ok"] = log.get("selected") is not False  # 선택 상태를 못 읽으면(None) 통과시키되 selected=None으로 남긴다
    time.sleep(1.5)
    rows = {}
    for col, n, c in _dataitems(appmod.wrap(hwnd)):
        if n == 0:
            rows[col] = _cell_value(c)
    log["row_names"] = list(rows)
    log["row_values"] = rows
    return log


def cell_same(want, got_list):
    """그리드 셀: 날짜는 숫자만, 금액은 공백·쉼표 제거 후 같음, 그 밖(콤보)은 값에 포함."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", want):
        d = re.sub(r"\D", "", want)
        return any(re.sub(r"\D", "", g) == d for g in got_list)
    w = re.sub(r"[\s,]", "", want)
    n = [re.sub(r"[\s,]", "", g) for g in got_list]
    return any(w == g or (not w.isdigit() and w in g) for g in n)


def op_grid_cell(hwnd, grid_id, row, want, record=0, method=None):
    """세로형 DevExpress 그리드 셀 입력. 열이름 row의 DataItem(레코드 record)을 찾아
    (a) ValuePattern.SetValue → 다시 읽기, (b) 안 되면 값 영역(너비 65% 지점) PostMessage 클릭 → 전경 확인 →
    Ctrl+A → 클립보드 붙여넣기 → Tab → 다시 읽기. method: set_value(기본, 실패 시 mouse로 이어짐) | mouse | post."""
    from pywinauto.keyboard import send_keys

    def locate():
        g = find_el(appmod.wrap(hwnd), grid_id)
        if g is None:
            return None, []
        items = _dataitems(g)
        cols = [c for c, n, _ in items if n == record]
        hit = [e for c, n, e in items if n == record and norm(c) == norm(row)]
        return (hit[0] if hit else None), cols

    c, cols = locate()
    if c is None:
        return {"found": False, "rows": cols}
    log = {"found": True, "rows": cols, "attempts": [], "foreground": [], "ok": False,
           "enabled": bool(c.element_info.enabled), "before": _cell_value(c)}
    if not log["enabled"]:
        return log

    def reread():
        c2, _ = locate()
        return [_cell_value(c2)] if c2 is not None else []

    if method in (None, "set_value"):
        att = {"method": "set_value", "already_equal": cell_same(want, [log["before"]])}
        try:
            c.iface_value.SetValue(want)
            time.sleep(0.4)
            att["read"] = reread()
            att["match"] = cell_same(want, att["read"])
        except Exception as e:  # noqa: BLE001
            att["error"] = f"{type(e).__name__}: {e}"
            att["match"] = False
        log["attempts"].append(att)
        if att["match"]:
            log.update(ok=True, method="set_value", read=att["read"])
            return log
    # (b) 셀 값 영역(너비 65% 지점)을 눌러 편집기를 켜고 입력한다.
    #   mouse: 실제 마우스 클릭(기본) — PostMessage 클릭은 이 그리드에서 셀 포커스를 옮기지 못했다(시험 확인).
    #   post : PostMessage 클릭. 입력은 날짜면 숫자만 type_keys(마스크 칸), 아니면 Ctrl+A 후 클립보드 붙여넣기.
    how = "post" if method == "post" else "mouse"
    okfg, seen = fg_ensure(hwnd)
    log["foreground"].append({"before": how, "ok": okfg, "hwnds": seen})
    if not okfg:
        return log
    att = {"method": how + "+" + ("type" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", want) else "paste")}
    try:
        c, _ = locate()
        r = c.element_info.rectangle
        x, y = r.left + int(r.width() * 0.65), (r.top + r.bottom) // 2
        if how == "post":
            att["click_hwnd"] = appmod.post_click_at(hwnd, x, y)
        else:
            from pywinauto import mouse
            mouse.click(coords=(x, y))
        time.sleep(0.8)
        okfg, seen = fg_ensure(hwnd)
        log["foreground"].append({"before": "input", "ok": okfg, "hwnds": seen})
        if not okfg:
            log["attempts"].append(att)
            return log
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", want):
            send_keys(re.sub(r"\D", "", want))
        else:
            send_keys("^a")
            time.sleep(0.15)
            set_clipboard(want)
            send_keys("^v")
        time.sleep(0.4)
        send_keys("{TAB}")
        time.sleep(0.6)
        att["read"] = reread()
        att["match"] = cell_same(want, att["read"])
    except Exception as e:  # noqa: BLE001
        att["error"] = f"{type(e).__name__}: {e}"
        att["match"] = False
    log["attempts"].append(att)
    if att["match"]:
        log.update(ok=True, method=att["method"], read=att["read"])
    else:
        log["read"] = att.get("read", [])
    return log


def op_click_id(hwnd, auto_id):
    """auto_id로 Button을 찾아 중앙에 PostMessage 클릭. (이름이 같은 버튼이 여럿일 때 쓴다) 반환: (찾음, 활성, 클릭받은 hwnd, 이름)"""
    el = find_el(appmod.wrap(hwnd), auto_id, "Button")
    if el is None:
        return (False, False, 0, "")
    e = el.element_info
    if not e.enabled:
        return (True, False, 0, e.name or "")
    r = e.rectangle
    return (True, True, appmod.post_click_at(hwnd, (r.left + r.right) // 2, (r.top + r.bottom) // 2), e.name or "")


def op_click_id_mouse(hwnd, auto_id):
    """auto_id인 첫 요소(종류 무관)의 중앙을 실제 마우스로 클릭(읽기 전용 칸 등). 1.0초 대기."""
    el = find_el(appmod.wrap(hwnd), auto_id)
    if el is None:
        return {"found": False}
    r = el.element_info.rectangle
    log = {"found": True, "enabled": bool(el.element_info.enabled), "rect": [r.left, r.top, r.right, r.bottom],
           "foreground": [], "ok": False}
    okfg, seen = fg_ensure(hwnd)
    log["foreground"].append({"before": "mouse", "ok": okfg, "hwnds": seen})
    if not okfg:
        return log
    from pywinauto import mouse
    mouse.click(coords=((r.left + r.right) // 2, (r.top + r.bottom) // 2))
    time.sleep(1.0)
    log["ok"] = True
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
    bad = a.unexpected_windows()
    if bad:
        print(f"경고: 예상 밖 창 {[(w.title, w.cls, why) for w, why in bad]} — 종료")
        return 2
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

    stopped = None
    for i, s in enumerate(steps, 1):
        if stopped:
            break
        k = action_of(s)
        if k in ("window", "close"):
            stopped = f"단계 {i} {k}: {s[k]!r} — 이후 단계는 그 창이 열려야 확인할 수 있어 생략"
            break
        if k == "radio_id":
            t = ids.get(s[k] if isinstance(s[k], str) else s[k]["id"])
            add(i, k, str(s[k]), find_status(bool(t) and t[0] == "RadioButton", bool(t) and t[2]))
            continue
        if k == "click_id":
            t = ids.get(s[k])
            add(i, k, str(s[k]), find_status(bool(t), bool(t) and t[2]))
            continue
        if k == "tab":
            t = next((x for x in inv if x[0] == "TabItem" and norm(x[1]) == norm(s[k])), None)
            add(i, k, s[k], find_status(bool(t), bool(t) and t[3]))
            continue
        if k == "grid_cell":
            t = ids.get(s[k]["grid"])
            add(i, k, f"{s[k]['grid']}/{s[k]['row']}", find_status(bool(t), bool(t) and t[2]))
            continue
        if k == "press":
            nm = s["press"]
            st = btns.get(norm(nm))
            add(i, "press", nm, find_status(st is not None, bool(st) and any(st)))
            if s.get("opens"):
                stopped = f"단계 {i} press opens {s['opens']!r} — 이후 단계는 그 창이 열려야 확인할 수 있어 생략"
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
    if stopped:
        print(f"\n{stopped}")
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
    def __init__(self, a, hwnd, case, base_window=""):
        self.a, self.hwnd, self.case, self.base_window = a, hwnd, case, base_window
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
        hit = key if key in mm else next((k for k in mm if _modal_match(k, key)), None)
        if hit is None:
            item["handled"] = False
            item["capture"] = self.shot_modal(w, "modal_unknown")
            raise Stop("abort", f"처음 보는 모달 {key!r} — 아무것도 누르지 않음. 단계 파일 modals에 추가 필요")
        for b in mm[hit]:
            if not self.a.press(w.hwnd, b):
                item["capture"] = self.shot_modal(w, "modal_nobutton")
                raise Stop("abort", f"모달 {key!r}에서 버튼 {b!r}을 누를 수 없음")
            item.setdefault("pressed", []).append(b)
        gone = appmod.wait_for(lambda: w.hwnd not in self.a.modals(), 4)
        item["handled"] = bool(gone)
        if not gone:
            raise Stop("abort", f"모달 {key!r}이(가) 닫히지 않음")

    def handle_open_modals(self, step, rec):
        """단계 시작 시 이미 열려 있는 모달(이전 단계 settle이 끝난 뒤 늦게 뜬 것) 처리:
        단계 modals에 맞으면 처리해 rec["modals_at_start"]에 기록, 없으면 캡처 후 중단."""
        for w in self.a.modals_info():
            key = self.a.modal_key(w)
            mm = [norm(k) for k in (step.get("modals") or {})]
            if not (key in mm or any(_modal_match(k, key) for k in mm)):
                self.shot_modal(w, "modal_at_start")
                raise Stop("abort", f"단계 시작 시 열려 있는 모달 {key!r} — 단계 파일 modals에 추가 필요")
            tmp = {}
            try:
                self.handle_modal(w, step, tmp)
            finally:
                rec.setdefault("modals_at_start", []).extend(tmp.get("modals", []))
            time.sleep(0.6)

    def settle(self, step, rec, before, base_wait=0.8):
        """누르거나 입력한 뒤: 새 모달은 단계 파일 규칙대로 처리, 새 화면·외부 창은 중단."""
        self.a.mark_op()
        appmod.wait_for(lambda: set(self.a.modals()) - before[1] or set(self.a.screens()) - before[0], 2.0, 0.25)
        time.sleep(base_wait)
        for _ in range(5):
            new = [w for w in self.a.modals_info() if w.hwnd not in before[1]]
            if not new:
                break
            for w in new:
                self.handle_modal(w, step, rec)
            time.sleep(0.6)
        opens = norm(step.get("opens") or "")
        if opens:
            appmod.wait_for(lambda: find_target(self.a, opens), 20.0, 0.5)
            time.sleep(1.0)
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
            if smap[tk] == "@close":  # 버튼 대신 WM_CLOSE로 닫는다(닫으며 뜨는 모달은 step의 modals 규칙)
                appmod._u32.PostMessageW(h, 0x0010, 0, 0)
                time.sleep(0.8)
                for _ in range(3):
                    for m in [x for x in self.a.modals_info() if x.hwnd not in before[1]]:
                        self.handle_modal(m, step, rec)
                        time.sleep(0.5)
            elif not self.a.press(h, smap[tk]):
                raise Stop("abort", f"화면 {w.title!r}에서 버튼 {smap[tk]!r}을 누를 수 없음")
            if not appmod.wait_for(lambda h=h: h not in self.a.screens(), 5.0):
                raise Stop("fail", f"화면 {w.title!r}이(가) 5초 안에 닫히지 않음")
            time.sleep(0.5)
            new_s.discard(h)
        if opens:
            for h in sorted(new_s):
                w = next((x for x in self.a.screens_info() if x.hwnd == h), None)
                if w and norm(clean_title(w.title)) == opens:
                    self.hwnd = h
                    cp = SCREENS / f"{self.case}_{self.i:02d}_opened.png"
                    rec["opened"] = {"title": w.title, "hwnd": h, "capture": str(cp.relative_to(ROOT)).replace("\\", "/"),
                                     "capture_method": self.a.capture(h, cp)}
                    new_s.discard(h)
            cur = next((x.title for x in self.a.screens_info() if x.hwnd == self.hwnd), "")
            if norm(clean_title(cur)) != opens:
                raise Stop("fail", f"opens {opens!r} 창이 열리지 않음")
        if new_s:
            rec["new_screens"] = sorted(new_s)
            self.shot("new_screen")
            raise Stop("abort", f"새 화면이 떴다 {sorted(new_s)} — 단계 파일에 반영 필요")
        new_e = set(self.a.externals()) - before[2]
        if new_e:
            aborts, ignored = self.a.judge_externals(new_e)
            if ignored:
                rec.setdefault("externals_ignored", []).extend(ignored)
            if aborts:
                rec["new_externals"] = aborts
                raise Stop("abort", f"외부 창이 떴다 {rec['new_externals']}")

    def no_unexpected(self):
        """누르기 직전 검사: 예상 밖 창이 있으면 캡처하고 중단."""
        why = self.a.halt_if_unexpected(f"{self.case}_{self.i:02d}")
        if why:
            raise Stop("abort", why)

    def check_closes(self, step, rec):
        """closes: <창 제목> — 누른 뒤 5초 안에 그 창이 사라지면 True(대상 창을 최상위 window로 되돌림). 아니면 기록만."""
        name = step.get("closes")
        if not name:
            return False
        gone = bool(appmod.wait_for(lambda: find_target(self.a, name) is None, 5.0))
        rec["closes"] = {"title": name, "gone": gone}
        if gone:
            base = find_target(self.a, self.base_window) if self.base_window else None
            if base:
                self.hwnd = base.hwnd
        return gone

    # -- 동작
    def do_press(self, step, rec):
        name = step["press"]
        self.no_unexpected()
        if self.a.is_forbidden(name):
            raise Stop("abort", f"금지 목록에 걸리는 버튼 {name!r}")
        st = self.btn_states().get(norm(name))
        # st가 None이어도(접근성 이름이 화면 글자와 다른 버튼) win32 글자로 누를 수 있으니 아래 press에 맡긴다
        if st is not None and not any(st):
            raise Stop("fail", f"버튼 비활성 {name!r}")
        before = self.snap()
        how = "postmessage"
        if not self.a.press(self.hwnd, name):
            how = "uia좌표"
            if not guard(lambda: op_click_button(self.hwnd, name)):
                raise Stop("fail", f"버튼을 누를 수 없음 {name!r}")
        rec["how"] = how
        self.settle(step, rec, before)
        if self.check_closes(step, rec):
            return
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

    def do_press_id(self, step, rec):
        aid = step["press_id"]
        self.no_unexpected()
        before = self.snap()
        found, enabled, h, name = guard(lambda: op_click_id(self.hwnd, aid))
        rec["button"] = {"id": aid, "name": name, "click_hwnd": h}
        if not found:
            raise Stop("fail", f"버튼을 못 찾음 {aid}")
        if self.a.is_forbidden(name):
            raise Stop("abort", f"금지 목록에 걸리는 버튼 {name!r} ({aid})")
        if not enabled:
            raise Stop("fail", f"버튼 비활성 {aid}")
        self.settle(step, rec, before)
        if self.check_closes(step, rec):
            return
        exp_en = step.get("expect_enabled") or []
        exp_dis = step.get("expect_disabled") or []
        if exp_en or exp_dis:
            last = {}

            def ok():
                last.update(self.btn_states())
                return (all(any(last.get(norm(b), [False])) for b in exp_en)
                        and all(norm(b) in last and not any(last[norm(b)]) for b in exp_dis))

            if not appmod.wait_for(ok, 6.0, 0.7):
                raise Stop("fail", f"기대 상태와 다름 enabled={exp_en} disabled={exp_dis}")

    def do_click_id(self, step, rec):
        aid = step["click_id"]
        self.no_unexpected()
        before = self.snap()
        res = guard(lambda: op_click_id_mouse(self.hwnd, aid))
        rec["result"] = res
        self.settle(step, rec, before, base_wait=0.3)
        if not res["found"]:
            raise Stop("fail", f"요소를 못 찾음 {aid}")
        if res["foreground"] and not res["foreground"][-1]["ok"]:
            raise Stop("fail", f"전경 창이 대상 창이 아님 {res['foreground'][-1]['hwnds']} (대상 {self.hwnd})")

    def _input(self, step, rec, kind):
        sp = step[kind]
        want = str(sp["value"])
        ctype = sp.get("type") or ("Edit" if kind == "text" else "ComboBox")  # type: Pane 등으로 바꿀 수 있다
        use_name = ctype not in ("Edit", "ComboBox")
        title0 = clean_title(next((w.title for w in self.a.screens_info() if w.hwnd == self.hwnd), ""))
        save0 = self.btn_states().get(norm("저장")) if kind == "combo" else None
        before = self.snap()
        if kind == "combo" and sp.get("mode", "select") == "select":
            res = guard(lambda: op_combo_select(self.hwnd, sp["id"], want))
        else:  # text 칸, 또는 combo mode: text(글자 방식)
            res = guard(lambda: op_input(self.hwnd, sp["id"], ctype, want, kind, use_name))
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
            raise Stop("fail", f"값이 들어가지 않음 {sp['id']} 원하는={want!r} 읽은={res.get('read')}"
                               + (f" 항목={res.get('items')} 선택={res.get('selection')}" if "items" in res else ""))
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
        if status == "window_gone":
            return  # 대상 창이 없다: 기록만 하고 계속
        if status == "failed":
            raise Stop("fail", "캡처 실패")

    def do_window(self, step, rec):
        name = step["window"]
        w = appmod.wait_for(lambda: find_target(self.a, name), 10.0, 0.5)
        if not w:
            raise Stop("fail", f"창 {name!r}을(를) 찾을 수 없음")
        self.hwnd = w.hwnd
        rec["hwnd"] = w.hwnd

    def do_radio_id(self, step, rec):
        sp = step["radio_id"]
        aid = sp if isinstance(sp, str) else sp["id"]
        before = self.snap()
        res = guard(lambda: op_radio_id(self.hwnd, aid))
        rec["result"] = res
        self.settle(step, rec, before, base_wait=0.4)
        if not res["found"]:
            raise Stop("fail", f"라디오를 못 찾음 {aid}: {res.get('why')}")
        if not res["enabled"]:
            raise Stop("fail", f"라디오 비활성 {aid}")
        if not res.get("ok"):
            raise Stop("fail", f"라디오가 선택되지 않음 {aid} ({res.get('method')})")

    def do_tab(self, step, rec):
        name = step["tab"]
        before = self.snap()
        res = guard(lambda: op_tab(self.hwnd, name), 60)
        rec["result"] = res
        self.settle(step, rec, before, base_wait=0.2)
        if not res["found"]:
            raise Stop("fail", f"탭을 못 찾음 {name!r} 탭들={res.get('tabs')}")
        if not res.get("ok"):
            raise Stop("fail", f"탭이 선택되지 않음 {name!r} ({res.get('method')})")

    def do_grid_cell(self, step, rec):
        sp = step["grid_cell"]
        want = str(sp["value"])
        before = self.snap()
        res = guard(lambda: op_grid_cell(self.hwnd, sp["grid"], sp["row"], want, int(sp.get("record", 0)), sp.get("method")), 90)
        rec["result"], rec["want"] = res, want
        self.settle(step, rec, before, base_wait=0.3)
        if not res["found"]:
            raise Stop("fail", f"그리드 셀을 못 찾음 {sp['grid']}/{sp['row']} 행들={res.get('rows')}")
        if not res["enabled"]:
            raise Stop("fail", f"셀 비활성 {sp['row']}")
        if res["foreground"] and not res["foreground"][-1]["ok"]:
            raise Stop("fail", f"전경 창이 대상 창이 아님 {res['foreground'][-1]['hwnds']} (대상 {self.hwnd})")
        if not res["ok"]:
            raise Stop("fail", f"셀 값이 들어가지 않음 {sp['row']} 원하는={want!r} 시도={res['attempts']}")

    def do_close(self, step, rec):
        """창 닫기(WM_CLOSE). 닫으며 뜨는 모달은 step의 modals 규칙으로 처리한다. 끝나면 기본 창으로 되돌린다."""
        name = step["close"]
        w = find_target(self.a, name)
        if not w:
            raise Stop("fail", f"창 {name!r}을(를) 찾을 수 없음")
        before = self.snap()
        appmod._u32.PostMessageW(w.hwnd, 0x0010, 0, 0)
        self.settle(step, rec, before, base_wait=0.8)
        gone = appmod.wait_for(lambda: w.hwnd not in self.a.screens(), 6.0)
        rec["closed"] = bool(gone)
        if not gone:
            raise Stop("fail", f"창 {name!r}이(가) 닫히지 않음")
        base = find_target(self.a, self.base_window) if self.base_window else None
        if base:
            self.hwnd = base.hwnd

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
                self.handle_open_modals(step, rec)  # F8: 늦게 뜬 모달이 다음 단계 입력을 막지 않게 먼저 처리
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
        why = a.halt_if_unexpected(f"{case}_start")
        if why:
            raise Stop("abort", why)
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
        runner = Runner(a, w.hwnd, case, window)
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
