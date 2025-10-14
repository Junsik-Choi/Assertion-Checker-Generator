"""
Simulate exact onboarding flow: EDA/RTL -> 9 -> auto detected (enter)
"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import (
    AppState, 
    _create_session_excel_and_fill,
    _save_session_snapshot,
    build_context_from_rtl
)

print("=" * 80)
print("SIMULATING ONBOARDING: EDA/RTL -> 9 -> auto detected (enter)")
print("=" * 80)

# Step 1: Create state
state = AppState()
print("\n[STEP 1] Initial state created")

# Step 2: Set RTL path
state.rtl_start = Path("EDA/RTL").resolve()
print(f"[STEP 2] RTL path set: {state.rtl_start}")

# Step 3: Build context from RTL
print(f"[STEP 3] Building context from RTL...")
try:
    modules, mi, occs = build_context_from_rtl(state.rtl_start, None)
    state.modules_db = modules
    state.module_info = mi
    state.occs = occs
    print(f"          Found {len(modules)} modules")
    
    # List modules
    module_list = sorted(modules.keys())
    print(f"          Modules: {module_list}")
    
    # Step 4: Select module #9 (index 8)
    if len(module_list) > 8:
        state.target_module = module_list[8]
        print(f"[STEP 4] Selected module #9: {state.target_module}")
        
        # Refresh module_info for selected module
        modules, mi, occs = build_context_from_rtl(state.rtl_start, state.target_module)
        state.modules_db = modules
        state.module_info = mi
        state.occs = occs
        print(f"          Module info refreshed")
        print(f"          Module: {mi.module}")
        print(f"          Ports: {len(mi.inputs)} inputs, {len(mi.outputs)} outputs")
    else:
        print(f"[ERROR] Not enough modules! Only {len(module_list)} found")
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR] Failed to build context: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: Auto-detect Excel
print(f"[STEP 5] Auto-detecting Excel...")
excel_candidates = [
    Path("Data/Assertion_TF.xlsx"),
    Path("define.xlsx"),
]

for candidate in excel_candidates:
    if candidate.exists():
        state.excel_path = candidate.resolve()
        state.onboarding_excel_autofound = candidate.resolve()
        print(f"          Found: {state.excel_path}")
        break
else:
    print(f"[ERROR] No Excel found!")
    sys.exit(1)

# Step 6: Simulate pressing Enter (using autofound Excel)
print(f"[STEP 6] Simulating Enter (use autofound Excel)...")
print(f"          Excel path: {state.excel_path}")
print(f"          Autofound: {state.onboarding_excel_autofound}")

# This is what happens in onboarding when user presses Enter
state.onboarding_active = False
state.onboarding_stage = None

print(f"\n[STEP 7] Calling _create_session_excel_and_fill()...")
print(f"          state.excel_path: {state.excel_path}")
print(f"          state.target_module: {state.target_module}")
print(f"          state.module_info.module: {state.module_info.module}")
print(f"          state.session_excel_path (before): {state.session_excel_path}")

ok, err = _create_session_excel_and_fill(state)

print(f"\n[STEP 8] Result:")
print(f"          Success: {ok}")
print(f"          Message: {err}")
print(f"          state.session_excel_path (after): {state.session_excel_path}")

if ok:
    print(f"\n[STEP 9] Saving session snapshot...")
    _save_session_snapshot(state)
    print(f"          Snapshot saved")
else:
    print(f"\n[ERROR] Session creation failed!")

# Check what was created
print(f"\n[VERIFICATION]")
sessions_dir = Path("out/sessions")
if sessions_dir.exists():
    items = list(sessions_dir.iterdir())
    print(f"Sessions directory contents ({len(items)} items):")
    for item in sorted(items, key=lambda x: x.stat().st_mtime, reverse=True):
        if item.is_dir():
            print(f"  📂 {item.name}/")
            for sub in sorted(item.iterdir()):
                size = sub.stat().st_size if sub.is_file() else 0
                print(f"     📄 {sub.name} ({size:,} bytes)")
        else:
            size = item.stat().st_size
            print(f"  📄 {item.name} ({size:,} bytes)")
else:
    print(f"❌ Sessions directory not found!")

# Check debug log
debug_log = Path("out/session_creation_debug.log")
if debug_log.exists():
    print(f"\n[DEBUG LOG]")
    print(debug_log.read_text(encoding="utf-8"))

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
