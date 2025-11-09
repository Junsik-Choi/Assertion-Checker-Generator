"""
Clear debug log and show current state
"""
from pathlib import Path

debug_log = Path("out/session_creation_debug.log")

if debug_log.exists():
    debug_log.unlink()
    print(f"✓ Cleared debug log: {debug_log}")
else:
    print(f"ℹ️ Debug log doesn't exist yet: {debug_log}")

print("\nNow run TUI and perform 'new' operation.")
print("After completing, run: python show_debug_log.py")
