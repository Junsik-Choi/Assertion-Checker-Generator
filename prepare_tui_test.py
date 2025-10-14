"""
TUI 테스트를 위한 준비 스크립트
"""
from pathlib import Path
from datetime import datetime

# 디버그 로그 초기화
debug_log = Path("out/session_creation_debug.log")
if debug_log.exists():
    debug_log.unlink()

# 세션 폴더 정리
import shutil
sessions_dir = Path("out/sessions")
if sessions_dir.exists():
    for item in sessions_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

print("=" * 80)
print("TUI TEST PREPARATION")
print("=" * 80)
print(f"\n✓ Debug log cleared")
print(f"✓ Sessions directory cleared")
print(f"\nCurrent time: {datetime.now().strftime('%H:%M:%S')}")
print("\n" + "=" * 80)
print("NOW RUN TUI AND PERFORM ONBOARDING:")
print("=" * 80)
print("\n1. Run: cd scripts ; python cli_tui.py")
print("2. Input: EDA/RTL")
print("3. Select: 9")
print("4. Press: Enter (use auto-detected Excel)")
print("5. Quit: q")
print("\n" + "=" * 80)
print("AFTER TUI, RUN: python check_tui_result.py")
print("=" * 80)
