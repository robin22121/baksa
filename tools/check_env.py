"""윈도우 환경 점검 (W1). 사용: python tools/check_env.py [--title 양도박사]"""
import argparse
import os
import platform
import shutil
import struct
import sys

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


def _count_controls(dump_text):
    counts = {}
    for key in ("Edit", "Button", "Grid", "DataGrid", "Table", "DataItem", "MenuItem", "ComboBox", "Pane"):
        n = dump_text.count(f"- {key}")
        if n:
            counts[key] = n
    return counts


def check_window(title):
    print("[양도박사 창 컨트롤 노출]")
    if not IS_WIN:
        print(f"  {SKIP}")
        return
    try:
        from pywinauto import Desktop
    except ImportError:
        print("  pywinauto 미설치")
        return
    import contextlib
    import io

    found_any = False
    for backend in ("uia", "win32"):
        try:
            wins = Desktop(backend=backend).windows(title_re=f".*{title}.*")
        except Exception as e:  # noqa: BLE001
            print(f"  [{backend}] 창 검색 실패: {e}")
            continue
        if not wins:
            continue
        found_any = True
        w = wins[0]
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                w.print_control_identifiers(depth=2)
            text = buf.getvalue()
            print(f"  [{backend}] 창: {w.window_text()!r}")
            print(f"  [{backend}] 컨트롤 요약: {_count_controls(text) or '식별된 컨트롤 없음'}")
            print(text)
            return
        except Exception as e:  # noqa: BLE001
            print(f"  [{backend}] print_control_identifiers 실패: {e}")
    if not found_any:
        print("  양도박사를 먼저 실행하세요")


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
