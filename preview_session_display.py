"""
세션 로더 화면 미리보기 (경로 표시 테스트)
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, 'scripts')
from cli_tui import _sanitize_path_for_display, _shorten_path_for_display

print("=" * 80)
print("세션 로더 화면 미리보기")
print("=" * 80)

# Get sessions
sessions_dir = Path("out/sessions")
if not sessions_dir.exists():
    print("세션 디렉터리가 없습니다!")
    sys.exit(1)

sessions = []
for p in sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        sessions.append(obj)
    except Exception:
        continue

if not sessions:
    print("저장된 세션이 없습니다!")
    sys.exit(1)

print(f"\n발견된 세션: {len(sessions)}개\n")

# Simulate column widths (typical terminal size)
no_w = 6
mod_w = 18
rtl_w = 50
xls_w = 20
out_w = 18

print("┌" + "─" * 78 + "┐")
print(f"│ {'No':<{no_w}} {'Module':<{mod_w}} {'RTL':<{rtl_w}} {'Excel':<{xls_w}} {'Out':<{out_w}} │")
print("├" + "─" * 78 + "┤")

for i, s in enumerate(sessions[:5], 1):  # Show first 5
    num = f"[{i}]"
    module = (s.get('target_module', '') or '')[:mod_w]
    
    rtl_full = s.get('rtl_start', '') or ''
    rtl_display = _shorten_path_for_display(rtl_full, rtl_w, keep_segments=3)
    
    xls_path = s.get('session_excel_path', '') or s.get('excel_path', '') or ''
    xls = Path(xls_path).name if xls_path else ''
    xls = xls[:xls_w]
    
    outp = _shorten_path_for_display(s.get('out_dir', '') or '', out_w)
    
    # Print row
    print(f"│ {num:<{no_w}} {module:<{mod_w}} {rtl_display:<{rtl_w}} {xls:<{xls_w}} {outp:<{out_w}} │")

print("└" + "─" * 78 + "┘")

print("\n" + "=" * 80)
print("설명:")
print("  [*] = 한글 문자가 있던 위치를 표시")
print("  경로가 길 경우 중요한 부분만 표시됨")
print("=" * 80)
