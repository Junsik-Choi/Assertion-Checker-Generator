"""
Test complete onboarding flow with session creation
"""
import sys
import json
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _create_session_excel_and_fill, _save_session_snapshot, AppState, ModuleInfo

# Create mock state like onboarding would
state = AppState()
state.excel_path = Path("define.xlsx").resolve()
state.target_module = "out_sync_gen"
state.module_info = ModuleInfo()
state.module_info.module = "out_sync_gen"
state.module_info.clocks = []
state.module_info.resets = []
state.module_info.inputs = []
state.module_info.outputs = []
state.module_info.inouts = []
state.module_info.parameters = []
state.conditions = []
state.rtl_start = Path("EDA/RTL")
state.out_dir = Path("out/assertions")

print("=" * 80)
print("TESTING ONBOARDING FLOW")
print("=" * 80)
print(f"\n1. Initial state:")
print(f"   Excel path: {state.excel_path}")
print(f"   Session Excel path: {state.session_excel_path}")
print(f"   Target module: {state.target_module}")

print(f"\n2. Creating session Excel...")
ok, err = _create_session_excel_and_fill(state)

print(f"\n3. Result:")
print(f"   Success: {ok}")
if not ok:
    print(f"   Error: {err}")
else:
    print(f"   Message: {err}")
print(f"   Session Excel path: {state.session_excel_path}")

print(f"\n4. Saving session snapshot...")
_save_session_snapshot(state)

print(f"\n5. Reading saved snapshot...")
sessions_dir = Path("out/sessions")
snapshots = sorted(sessions_dir.glob("session_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
if snapshots:
    latest = snapshots[0]
    print(f"   Latest snapshot: {latest.name}")
    data = json.loads(latest.read_text(encoding="utf-8"))
    print(f"   Contents:")
    for key, val in data.items():
        print(f"      {key}: {val}")
    
    # Check if session_excel_path is set
    if data.get("session_excel_path"):
        print(f"\n   ✅ session_excel_path is set!")
    else:
        print(f"\n   ❌ session_excel_path is EMPTY!")
else:
    print("   ❌ No snapshots found!")

print(f"\n6. Checking session folder...")
folders = sorted([f for f in sessions_dir.iterdir() if f.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
if folders:
    latest_folder = folders[0]
    print(f"   Latest folder: {latest_folder.name}")
    contents = list(latest_folder.iterdir())
    print(f"   Contents ({len(contents)} files):")
    for item in contents:
        size = item.stat().st_size if item.is_file() else 0
        print(f"      - {item.name} ({size:,} bytes)")
else:
    print("   ❌ No session folders found!")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
