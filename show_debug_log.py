"""
Show debug log from session creation
"""
from pathlib import Path

debug_log = Path("out/session_creation_debug.log")

print("=" * 80)
print("SESSION CREATION DEBUG LOG")
print("=" * 80)

if debug_log.exists():
    content = debug_log.read_text(encoding="utf-8")
    print(content)
    print("=" * 80)
    print(f"Log file: {debug_log}")
    print(f"Size: {debug_log.stat().st_size} bytes")
else:
    print("❌ Debug log not found!")
    print(f"Expected at: {debug_log.absolute()}")
    print("\nThis means _create_session_excel_and_fill() was NOT called!")

print("=" * 80)
