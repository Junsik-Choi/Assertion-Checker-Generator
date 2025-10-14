"""
Direct test of session creation logic
"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _create_session_excel_and_fill, AppState, ModuleInfo

# Create mock state
state = AppState()
state.excel_path = Path("define.xlsx").resolve()  # Use actual Excel file
state.target_module = "test_module"
state.module_info = ModuleInfo()
state.module_info.module = "test_module"
state.module_info.clocks = []
state.module_info.resets = []
state.module_info.inputs = []
state.module_info.outputs = []
state.module_info.inouts = []
state.module_info.parameters = []
state.conditions = []

print(f"Excel path exists: {state.excel_path.exists()}")
print(f"Target module: {state.target_module}")
print(f"Module info module: {state.module_info.module}")
print("\nCalling _create_session_excel_and_fill()...")

ok, err = _create_session_excel_and_fill(state)

print(f"\nResult: ok={ok}")
print(f"Error: {err}")
print(f"Session Excel path: {state.session_excel_path}")

# Check what was created
sessions_dir = Path(__file__).parent / "out" / "sessions"
if sessions_dir.exists():
    print(f"\n✓ Sessions directory exists: {sessions_dir}")
    folders = list(sessions_dir.glob("*"))
    print(f"  Contents ({len(folders)} items):")
    for item in folders:
        if item.is_dir():
            print(f"    [DIR]  {item.name}")
            sub_items = list(item.iterdir())
            for sub in sub_items:
                print(f"           - {sub.name}")
        else:
            print(f"    [FILE] {item.name}")
else:
    print("\n✗ Sessions directory does not exist!")
