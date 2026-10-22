"""윈도우 환경 점검 (W1). 사용: python tools/check_env.py [--title 양도박사]"""
import argparse
import os
import platform
import shutil
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKIP = "(Windows 아님 — 건너뜀)"
IS_WIN = platform.system() == "Windows"

TOOLS = {
    "psr.exe": [r"C:\Windows\System32\psr.exe"],
    "procmon.exe": [
        r"C:\Sysinternals\procmon.exe",
        r"C:\Program Files\Sysinternals\procmon.exe",
        r"C:\Program Files\SysinternalsSuite\procmon.exe",
        r"C:\Tools\procmon.exe",
    ],
    "HxD.exe": [
        r"C:\Program Files\HxD\HxD.exe",
        r"C:\Program Files (x86)\HxD\HxD.exe",
        r"C:\Program Files\HxD\HxD64.exe",
    ],
}


def check_basic():
    print("[OS/Python]")
    print(f"  OS: {platform.system()} {platform.release()} {platform.version()}")
    print(f"  Python: {platform.python_version()} ({struct.calcsize('P') * 8}비트)")


def check_odbc():
    print("[ODBC 드라이버]")
    if not IS_WIN:
        print(f"  {SKIP}")
        return
    try:
        import pyodbc
    except ImportError:
        print("  pyodbc 미설치")
        return
    drivers = pyodbc.drivers()
    if not drivers:
        print("  (없음)")
    for d in drivers:
        print(f"  - {d}")


def check_tools():
    print("[도구 존재 여부]")
    if not IS_WIN:
        print(f"  {SKIP}")
        return
    for name, paths in TOOLS.items():
        found = shutil.which(name) or next((p for p in paths if os.path.exists(p)), None)
        print(f"  {name}: {found if found else '없음'}")


def _count_controls(wrapper, backend):
    """descendants()를 control_type(uia) 또는 클래스(win32)별로 센다."""
    counts = {}
    for c in wrapper.descendants():
        key = c.element_info.control_type if backend == "uia" else c.friendly_class_name()
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def check_window(title):
    print("[양도박사 창 컨트롤 노출]")
    if not IS_WIN:
        print(f"  {SKIP}")
        return
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive"))
    try:
        import app as appmod  # DPI 인식을 pywinauto import 전에 켠다
    except ImportError as e:
        print(f"  app.py import 실패: {e}")
        return
    ok, why = appmod.available()
    if not ok:
        print(f"  {why}")
        return
    import contextlib
    import io

    pids = appmod.yd_pids()
    wins = [w for w in appmod.top_windows() if w.pid in pids and w.title and not w.owner and w.cls != "#32770"]
    if not wins:
        print("  양도박사를 먼저 실행하세요 (YDdoctor.exe 보이는 창 없음)")
        return
    w = next((x for x in wins if title in x.title), wins[0])
    if appmod.is_elevated(w.pid):
        print("  경고: 관리자 권한 실행 — RunAsInvoker로 다시 띄우세요 (일반 권한 Python은 읽기·캡처가 막힙니다)")
    from pywinauto import Desktop

    for backend in ("uia", "win32"):
        try:
            spec = Desktop(backend=backend).window(handle=w.hwnd)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                spec.print_control_identifiers(depth=3)
            summary = _count_controls(spec.wrapper_object(), backend)
            print(f"  [{backend}] 창: {w.title!r} (hwnd={w.hwnd})")
            print(f"  [{backend}] 컨트롤 요약: {summary or '식별된 컨트롤 없음'}")
            print(buf.getvalue())
            return
        except Exception as e:  # noqa: BLE001
            print(f"  [{backend}] 실패: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="양도박사", help="창 제목 패턴")
    args = ap.parse_args()
    check_basic()
    check_odbc()
    check_tools()
    check_window(args.title)
    print()
    print("이 출력을 docs/env.md의 '환경 점검 출력' 절에 붙이세요.")


if __name__ == "__main__":
    main()
