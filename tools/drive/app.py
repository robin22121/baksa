"""양도박사 GUI 조작 공통 (W1b). 실행은 사람이, 여기서는 떠 있는 창에 붙기만 한다.

Windows에서 손볼 곳은 TODO(win) 로 표시.
"""
import datetime
import platform
import re
import shutil
from pathlib import Path

try:
    from pywinauto import Application
except ImportError:
    Application = None

ROOT = Path(__file__).resolve().parents[2]
ENV_MD = ROOT / "docs" / "env.md"
LOG_PATH = ROOT / "docs" / "inventory" / "raw" / "drive.log"
BACKUP_ROOT = ROOT / "data" / "raw" / "backup"

SAFE_BUTTONS = ("취소", "닫기", "Cancel", "Close", "아니오", "No")


def available():
    """pywinauto 사용 가능 여부와 사유."""
    if platform.system() != "Windows":
        return False, "Windows 아님"
    if Application is None:
        return False, "pywinauto 없음"
    return True, ""


def log(action, result=""):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{action}\t{result}\n")


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
    """docs/env.md에서 금지 메뉴 목록과 데이터 폴더 경로를 읽는다."""
    text = ENV_MD.read_text(encoding="utf-8") if ENV_MD.exists() else ""
    forbidden = [l[2:].strip() for l in _section(text, "금지 메뉴") if l.startswith("- ") and l[2:].strip()]
    data_dir = None
    for l in _section(text, "데이터 폴더"):
        if l.startswith("- ") and l[2:].strip():
            data_dir = l[2:].strip()
            break
    return {"forbidden": forbidden, "data_dir": data_dir}


class App:
    def __init__(self):
        env = load_env()
        self.forbidden = env["forbidden"]
        self.data_dir = env["data_dir"]
        self.app = None
        self.main = None
        self.backend = "uia"

    def attach(self, title_re="양도박사", backend="uia"):
        ok, why = available()
        if not ok:
            raise RuntimeError(why)
        self.backend = backend
        self.app = Application(backend=backend).connect(title_re=f".*{title_re}.*")
        self.main = self.app.window(title_re=f".*{title_re}.*")
        log("attach", f"{title_re}/{backend}")
        return self.main

    def is_forbidden(self, menu_text):
        return any(f and f in menu_text for f in self.forbidden)

    def click_menu(self, path):
        """path: 메뉴 텍스트 리스트. 금지 단계가 있으면 클릭 없이 False."""
        for step in path:
            if self.is_forbidden(step):
                log("click_menu", f"차단 {' > '.join(path)}")
                return False
        try:
            # TODO(win): uia에서 menu_select 경로 구분자·MenuItem 직접 클릭 중 되는 쪽 확인
            self.main.menu_select("->".join(path))
            log("click_menu", f"ok {' > '.join(path)}")
            return True
        except Exception as e:  # noqa: BLE001
            log("click_menu", f"실패 {' > '.join(path)}: {e}")
            return False

    def dismiss_modal(self):
        """활성 모달이 있으면 SAFE_BUTTONS 텍스트 버튼만 누른다."""
        try:
            # TODO(win): 모달 탐지 방식 확인 (top_window() vs 별도 Dialog). 메인 창이면 건드리지 않음
            top = self.app.top_window()
            if top.handle == self.main.handle:
                return False
            for btn in top.descendants(control_type="Button") if self.backend == "uia" else top.children(class_name="Button"):
                text = btn.window_text().strip()
                if text in SAFE_BUTTONS:
                    btn.click_input()
                    log("dismiss_modal", f"{top.window_text()!r} -> {text}")
                    return True
            log("dismiss_modal", f"안전 버튼 없음 {top.window_text()!r}")
        except Exception as e:  # noqa: BLE001
            log("dismiss_modal", f"실패 {e}")
        return False

    def _data_path(self):
        if not self.data_dir:
            print("경고: docs/env.md의 '데이터 폴더 위치'가 비어 있음 — no-op")
            log("backup/restore", "데이터 폴더 미정, no-op")
            return None
        return Path(self.data_dir)

    def backup_data(self):
        src = self._data_path()
        if src is None:
            return None
        dst = BACKUP_ROOT / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copytree(src, dst)
        log("backup_data", str(dst))
        return dst

    def restore_data(self, backup=None):
        dst = self._data_path()
        if dst is None:
            return False
        if backup is None:
            cands = sorted(BACKUP_ROOT.glob("*")) if BACKUP_ROOT.exists() else []
            if not cands:
                print("경고: 백업 없음")
                return False
            backup = cands[-1]
        # TODO(win): 양도박사 종료 상태에서 복원할지, 파일 잠금 처리 확인
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(backup, dst)
        log("restore_data", str(backup))
        return True
