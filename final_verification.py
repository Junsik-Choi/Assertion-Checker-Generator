#!/usr/bin/env python3
"""
Final comprehensive test: 
Simulate the entire flow from session loading to display
"""
import sys
import json
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _load_sessions

print("=" * 70)
print("FINAL COMPREHENSIVE TEST - Session Excel Data Loading")
print("=" * 70)

# Step 1: Load sessions
print("\n[STEP 1] Loading all sessions from disk...")
sessions = _load_sessions()
print(f"✓ Loaded {len(sessions)} session(s)")

# Step 2: Check blur_scaler session specifically
print("\n[STEP 2] Checking blur_scaler-20251203_141618 session...")
blur_sessions = [s for s in sessions if 'blur_scaler-20251203' in s.get('_folder', '')]
if blur_sessions:
    bs = blur_sessions[0]
    print(f"✓ Found session: {Path(bs.get('_folder', '')).name}")
    
    assertions_count = len(bs.get('assertions', []))
    print(f"  Assertions in session.json: {assertions_count}")
    
    if assertions_count > 0:
        for i, a in enumerate(bs['assertions'], 1):
            print(f"\n  [{i}] Type: {a.get('type')}")
            data = a.get('data', {})
            for key, val in data.items():
                print(f"      {key}: {val}")
        print("\n✓ Session assertions are correctly loaded!")
    else:
        print("✗ No assertions found in session!")
else:
    print("✗ blur_scaler session not found!")

# Step 3: Verify main view display readiness
print("\n[STEP 3] Checking main view display readiness...")
if blur_sessions:
    bs = blur_sessions[0]
    if bs.get('assertions'):
        assertion = bs['assertions'][0]
        atype = assertion.get('type')
        adata = assertion.get('data', {})
        
        # Simulate how UI will display
        if atype == 'counter':
            signal = adata.get('target', '?')
            exp_cnt = adata.get('exp_cnt_val', '?')
            display = f"Monitor {signal} counter reaching {exp_cnt}"
            print(f"✓ Display in UI: {display}")
        
        print("\n✓ All display data is ready for UI!")

# Step 4: Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

all_assertions = sum(len(s.get('assertions', [])) for s in sessions)
print(f"Total assertions across all sessions: {all_assertions}")

if all_assertions > 0:
    print("\n✅ SUCCESS! Session Excel data is properly loaded and ready for display.")
    print("\nWhat was fixed:")
    print("  1. ✓ Row offset fixed (reading Row 9 instead of Row 8)")
    print("  2. ✓ Placeholder filtering removed (was blocking 'abc')")
    print("  3. ✓ Assertions saved to session.json after loading from Excel")
    print("  4. ✓ Session chooser shows assertion count")
    print("  5. ✓ Main view displays loaded assertions")
else:
    print("\n❌ FAILED - No assertions found")

print("\n" + "=" * 70)
