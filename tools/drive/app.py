"""양도박사 GUI 조작 공통 (W1b). 실행(로그인)은 사람이, 여기서는 떠 있는 창에 붙어 읽고 누르기만 한다.

화면·모달·누르기·캡처·지문의 정의는 docs/work-plans/2026-10-22-설치형-탐색기.md §2.
"""
# DPI 인식은 pywinauto를 import 하기 전에 켠다 (캡처 좌표가 실제 픽셀과 맞도록)
import ctypes
import ctypes.wintypes as wt
import platform

if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass

import datetime
import hashlib
import os
import re
import shutil
import subprocess
import threading
import time
from collections import namedtuple
from pathlib import Path

try:
    from pywinauto import Desktop
except ImportError:
    Desktop = None

ROOT = Path(__file__).resolve().parents[2]
ENV_MD = ROOT / "docs" / "env.md"
LOG_PATH = ROOT / "docs" / "inventory" / "raw" / "drive.log"
BACKUP_ROOT = ROOT / "data" / "raw" / "backup"

PROC_NAME = "YDdoctor.exe"
DEFAULT_EXE = r"C:\Neoic\Tax2019\YDdoctor.exe"
MAIN_MIN_BUTTONS = 26
PRESS_TIMEOUT = 5.0
BIG_FILE = 200 * 1024 * 1024  # 이 크기를 넘는 파일은 앞·뒤 1MB 표본 해시

Win = namedtuple("Win", "hwnd pid title cls owner msg", defaults=("",))

# 이 이름의 버튼만 있는 창(+짧은 문구)은 모달(메시지 상자), 아니면 화면
MODAL_BUTTONS = {"예", "아니오", "확인", "취소", "닫기"}

if platform.system() == "Windows":
    _u32 = ctypes.windll.user32
    _k32 = ctypes.windll.kernel32
    _adv = ctypes.windll.advapi32
    _u32.GetForegroundWindow.restype = wt.HWND
    _u32.GetDC.restype = wt.HDC
    _u32.GetWindow.restype = wt.HWND
    _u32.GetWindow.argtypes = [wt.HWND, wt.UINT]
    _u32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    _u32.IsWindowVisible.argtypes = [wt.HWND]
    _u32.IsWindow.argtypes = [wt.HWND]
    _u32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    _u32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    _u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    _u32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    _u32.PrintWindow.argtypes = [wt.HWND, wt.HDC, wt.UINT]
    _k32.OpenProcess.restype = wt.HANDLE
    _k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    _k32.CloseHandle.argtypes = [wt.HANDLE]
    _k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    _adv.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
    _adv.GetTokenInformation.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]


def available():
    """pywinauto 사용 가능 여부와 사유."""
    if platform.system() != "Windows":
        return False, "Windows 아님"
    if Desktop is None:
        return False, "pywinauto 없음"
    return True, ""


def log(action, result=""):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{action}\t{result}\n")


def norm(name):
    """버튼 이름 비교용: 공백을 모두 지운다."""
    return re.sub(r"\s+", "", name or "")


def _section(text, title):
    """'## ...title...' 절의 본문 줄들 (다음 '## ' 전까지)."""
    lines, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = title in line
            continue
        if inside:
            lines.append(line)
    return lines


def load_env():
    """docs/env.md에서 금지 메뉴 목록을 읽는다 (공백 제거 형태로)."""
    text = ENV_MD.read_text(encoding="utf-8") if ENV_MD.exists() else ""
    forbidden = [norm(l[2:]) for l in _section(text, "금지 메뉴") if l.startswith("- ") and l[2:].strip()]
    return {"forbidden": forbidden}


# ---- 저수준 창·프로세스 조회 (ctypes) ----

def _proc_path(pid):
    h = _k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wt.DWORD(1024)
        return buf.value if _k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ""
    finally:
        _k32.CloseHandle(h)


def proc_name(pid):
    return os.path.basename(_proc_path(pid))


def is_elevated(pid):
    """프로세스가 관리자 권한이면 True, 아니면 False, 알 수 없으면 None.
    토큰 접근이 거부되면 높은 권한 프로세스일 가능성이 커서 True로 본다."""
    h = _k32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    try:
        tok = wt.HANDLE()
        if not _adv.OpenProcessToken(h, 0x0008, ctypes.byref(tok)):  # TOKEN_QUERY
            return True
        try:
            val, ret = wt.DWORD(0), wt.DWORD(0)
            if _adv.GetTokenInformation(tok, 20, ctypes.byref(val), 4, ctypes.byref(ret)):  # TokenElevation
                return bool(val.value)
            return None
        finally:
            _k32.CloseHandle(tok)
    finally:
        _k32.CloseHandle(h)


def top_windows():
    """데스크톱의 보이는 최상위 창 전부 (Win 목록)."""
    out = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if _u32.IsWindowVisible(hwnd):
            pid = wt.DWORD()
            _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            t = ctypes.create_unicode_buffer(512)
            _u32.GetWindowTextW(hwnd, t, 512)
            c = ctypes.create_unicode_buffer(256)
            _u32.GetClassNameW(hwnd, c, 256)
            out.append(Win(int(hwnd), pid.value, t.value, c.value, int(_u32.GetWindow(hwnd, 4) or 0)))  # GW_OWNER
        return True

    _u32.EnumWindows(cb, 0)
    return out


def yd_pids():
    """YDdoctor.exe 프로세스의 pid 목록 (보이는 창을 가진 것)."""
    return sorted({w.pid for w in top_windows() if proc_name(w.pid).lower() == PROC_NAME.lower()})


def window_rect(hwnd):
    r = wt.RECT()
    _u32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def wrap(hwnd):
    """hwnd → uia 래퍼."""
    return Desktop(backend="uia").window(handle=hwnd).wrapper_object()


def wait_for(pred, timeout, interval=0.25):
    end = time.time() + timeout
    while True:
        v = pred()
        if v:
            return v
        if time.time() >= end:
            return v
        time.sleep(interval)


def win32_descendants(hwnd):
    return Desktop(backend="win32").window(handle=hwnd).descendants()


def call_with_timeout(fn, sec):
    """fn을 별도 스레드에서 실행해 결과를 돌려준다. 예외는 다시 던지고, sec초 넘으면 TimeoutError."""
    box = {}

    def work():
        try:
            try:
                import comtypes
                comtypes.CoInitializeEx()
            except Exception:  # noqa: BLE001
                pass
            box["v"] = fn()
        except Exception as e:  # noqa: BLE001
            box["e"] = e

    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(sec)
    if th.is_alive():
        raise TimeoutError(f"{sec}초 초과")
    if "e" in box:
        raise box["e"]
    return box["v"]


def _hwnd_of(win):
    return win if isinstance(win, int) else win.handle


class App:
    def __init__(self):
        self.forbidden = load_env()["forbidden"]
        self.main = None
        self.main_hwnd = None
        self.pids = []
        self.root = None  # 설치 폴더

    # ---- 시작·붙기 ----

    def start(self, exe=DEFAULT_EXE):
        """RunAsInvoker(일반 권한)로 실행만 한다. 로그인은 사람이 한다."""
        env = dict(os.environ, __COMPAT_LAYER="RunAsInvoker")
        subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env)
        log("start", exe)

    def attach(self):
        """프로세스 이름으로 붙는다. 사전 조건: 메인 창 1개 + Button 26개 이상."""
        ok, why = available()
        if not ok:
            raise RuntimeError(why)
        self.pids = yd_pids()
        if not self.pids:
            raise RuntimeError(f"{PROC_NAME} 프로세스 없음 — 양도박사를 실행하고 로그인하세요")
        mains = [w for w in self.screens_info() if w.title.startswith("양도박사")]
        if len(mains) != 1:
            raise RuntimeError(f"메인 창이 {len(mains)}개 — 사전 조건 위반(1개여야 함)")
        self.main_hwnd = mains[0].hwnd
        self.main = wrap(self.main_hwnd)
        n = len(self.main.descendants(control_type="Button"))
        if n < MAIN_MIN_BUTTONS:
            raise RuntimeError(f"메인 창 Button {n}개 < {MAIN_MIN_BUTTONS} — 로그인이 끝난 화면인지 확인")
        path = _proc_path(self.pids[0])
        self.root = Path(path).parent if path else Path(DEFAULT_EXE).parent
        log("attach", f"pids={self.pids} main={self.main_hwnd} buttons={n}")
        return self.main

    # ---- 화면·모달 ----

    def _yd_windows(self):
        pids = set(self.pids)
        return [w for w in top_windows() if w.pid in pids]

    def _split(self):
        """제목 있는 양도박사 보이는 최상위 창을 (화면, 모달)로 나눈다. 제목 없는 창은 둘 다 아님.
        #32770은 모달. 그 밖에는 win32 descendants 중 글자가 있는 컨트롤의 텍스트를 보고,
        {예,아니오,확인,취소,닫기}에 속하는 버튼 텍스트가 있고 그 밖의 문구가 2개 이하면 모달(msg=문구), 아니면 화면.
        (win32 클래스로는 버튼을 구분할 수 없어 텍스트로 판단한다. owner 유무는 보지 않는다.)"""
        screens, modals = [], []
        for w in self._yd_windows():
            if not w.title:
                continue
            if w.cls == "#32770":
                modals.append(w)
                continue
            try:
                texts = [t for t in (d.window_text().strip() for d in win32_descendants(w.hwnd)) if t]
            except Exception:  # noqa: BLE001
                texts = []
            btn = [t for t in texts if norm(t) in MODAL_BUTTONS]
            other = [t for t in texts if norm(t) not in MODAL_BUTTONS]
            if btn and len(other) <= 2:
                modals.append(w._replace(msg=" ".join(other)))
            else:
                screens.append(w)
        return screens, modals

    def screens_info(self):
        return self._split()[0]

    def modals_info(self):
        return self._split()[1]

    @staticmethod
    def modal_key(w):
        """모달 키: 제목|문구 (공백 제거)."""
        return norm(w.title) + "|" + norm(w.msg)

    def screens(self):
        """화면 hwnd 목록 (제목 있고 owner 없고 #32770 아님)."""
        return [w.hwnd for w in self.screens_info()]

    def modals(self):
        """모달 hwnd 목록 (owner 있거나 #32770)."""
        return [w.hwnd for w in self.modals_info()]

    def externals(self):
        """양도박사가 아닌 프로세스의 제목 있는 보이는 창 {hwnd: (제목, 프로세스명)}."""
        pids = set(self.pids)
        return {w.hwnd: (w.title, proc_name(w.pid)) for w in top_windows() if w.title and w.pid not in pids}

    # ---- 버튼 ----

    def buttons(self, win):
        """창 안의 Button 이름 목록(원문, 순서 유지, 빈 이름 제외). uia가 실패하거나 10초 넘으면 win32 텍스트로 대체."""
        hwnd = _hwnd_of(win)
        try:
            bs = call_with_timeout(lambda: wrap(hwnd).descendants(control_type="Button"), 10)
            names = [b.element_info.name or "" for b in bs]
        except Exception as e:  # noqa: BLE001
            log("buttons", f"uia 실패 → win32 {e}")
            names = [d.window_text() for d in win32_descendants(hwnd)]
        return [n for n in names if n.strip()]

    def is_forbidden(self, name):
        n = norm(name)
        return any(f and f in n for f in self.forbidden)

    def press(self, win, name):
        """금지 목록에 걸리면 누르지 않고 False. 아니면 win32로 이름이 같은 컨트롤을 찾아
        클라이언트 중앙에 WM_LBUTTONDOWN/UP을 PostMessage(비동기, ShowDialog에 막히지 않음). 못 찾으면 False."""
        if self.is_forbidden(name):
            log("press", f"차단 {name!r}")
            return False
        target = norm(name)
        try:
            for d in win32_descendants(_hwnd_of(win)):
                if norm(d.window_text()) == target:
                    r = d.client_rect()
                    lp = ((r.height() // 2) << 16) | (r.width() // 2)
                    _u32.PostMessageW(d.handle, 0x201, 1, lp)
                    _u32.PostMessageW(d.handle, 0x202, 0, lp)
                    log("press", f"ok {name!r}")
                    return True
        except Exception as e:  # noqa: BLE001
            log("press", f"실패 {name!r} {e}")
            return False
        log("press", f"버튼 없음 {name!r}")
        return False

    def close_screen(self, win, timeout=5.0):
        """WM_CLOSE로 닫는다. 창이 사라지면 True. 모달 처리는 호출자가 이어서 한다."""
        hwnd = _hwnd_of(win)
        _u32.PostMessageW(hwnd, 0x0010, 0, 0)
        gone = wait_for(lambda: not _u32.IsWindow(hwnd) or not _u32.IsWindowVisible(hwnd), timeout)
        log("close_screen", f"{hwnd} {'닫힘' if gone else '안 닫힘'}")
        return bool(gone)

    # ---- 캡처 ----

    def capture(self, win, path):
        """창을 맨 앞에 두고 화면 복사. 실패하면 PrintWindow. 반환: ok / printwindow / failed."""
        from PIL import Image, ImageGrab
        hwnd = _hwnd_of(win)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        w = wrap(hwnd)
        try:
            w.set_focus()
        except Exception as e:  # noqa: BLE001
            log("capture", f"set_focus 실패 {e}")
        time.sleep(0.4)
        l, t, r, b = window_rect(hwnd)
        if int(_u32.GetForegroundWindow() or 0) == hwnd:
            img = ImageGrab.grab(bbox=(l, t, r, b), all_screens=True)
            if any(img.convert("L").getextrema()):
                img.save(path)
                return "ok"
        # 포그라운드가 아니면 PrintWindow(PW_RENDERFULLCONTENT) 한 번
        hdc_screen = _u32.GetDC(0)
        gdi = ctypes.windll.gdi32
        mdc = gdi.CreateCompatibleDC(hdc_screen)
        bmp = gdi.CreateCompatibleBitmap(hdc_screen, r - l, b - t)
        gdi.SelectObject(mdc, bmp)
        okp = _u32.PrintWindow(hwnd, mdc, 2)
        status = "failed"
        if okp:
            bi = (ctypes.c_byte * 40)()
            ctypes.memmove(bi, (ctypes.c_uint32 * 1)(40), 4)
            w_, h_ = r - l, b - t
            ctypes.memmove(ctypes.addressof(bi) + 4, (ctypes.c_int32 * 2)(w_, -h_), 8)
            ctypes.memmove(ctypes.addressof(bi) + 12, (ctypes.c_uint16 * 2)(1, 32), 4)
            data = ctypes.create_string_buffer(w_ * h_ * 4)
            gdi.GetDIBits(mdc, bmp, 0, h_, data, bi, 0)
            img = Image.frombuffer("RGBA", (w_, h_), data, "raw", "BGRA", 0, 1).convert("RGB")
            if any(img.convert("L").getextrema()):
                img.save(path)
                status = "printwindow"
        gdi.DeleteObject(bmp)
        gdi.DeleteDC(mdc)
        _u32.ReleaseDC(0, hdc_screen)
        return status

    # ---- 데이터 보호 ----

    def fingerprint(self):
        """설치 폴더 전체 {상대경로: (크기, mtime, sha1)}. 200MB 초과 파일은 앞·뒤 1MB 표본 해시('s:' 접두)."""
        fp = {}
        for dp, _, files in os.walk(self.root):
            for fn in files:
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, self.root)
                try:
                    st = os.stat(p)
                    h = hashlib.sha1()
                    with open(p, "rb") as f:
                        if st.st_size <= BIG_FILE:
                            for chunk in iter(lambda: f.read(1 << 20), b""):
                                h.update(chunk)
                            digest = h.hexdigest()
                        else:
                            h.update(f.read(1 << 20))
                            f.seek(-(1 << 20), os.SEEK_END)
                            h.update(f.read(1 << 20))
                            digest = "s:" + h.hexdigest()
                    fp[rel] = (st.st_size, st.st_mtime, digest)
                except OSError as e:
                    fp[rel] = (-1, 0, f"err:{e.errno}")
        return fp

    @staticmethod
    def diff_fingerprint(before, after):
        """added/removed/content(크기 또는 sha1 변경)/mtime_only 분류."""
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        content, mtime_only = [], []
        for k in sorted(set(before) & set(after)):
            b, a = before[k], after[k]
            if b[0] != a[0] or b[2] != a[2]:
                content.append(k)
            elif b[1] != a[1]:
                mtime_only.append(k)
        return {"added": added, "removed": removed, "content": content, "mtime_only": mtime_only}

    def backup_before_run(self):
        """Data\\neoTax.fdb 와 설치 루트의 *.ini 를 data/raw/backup/<시각>/ 에 복사. 복사 실패는 목록으로 돌려준다."""
        dst = BACKUP_ROOT / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst.mkdir(parents=True, exist_ok=True)
        srcs = [self.root / "Data" / "neoTax.fdb", self.root / "Data" / "neoPost.fdb"] + sorted(self.root.glob("*.ini"))
        failed = []
        for s in srcs:
            try:
                t = dst / s.relative_to(self.root)
                t.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, t)
            except OSError as e:
                failed.append(f"{s.name}: {e}")
        log("backup_before_run", f"{dst} 실패={failed}")
        return dst, failed
