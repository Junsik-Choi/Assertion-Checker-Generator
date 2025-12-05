#!/usr/bin/env python3
"""
Check if hierarchy, input, output, clocks, resets are loaded from session
"""
import sys
import json
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _load_sessions

print("=" * 70)
print("MODULE INFO VERIFICATION (hierarchy, inputs, outputs, clocks, resets)")
print("=" * 70)

sessions = _load_sessions()

for session in sessions:
    module = session.get('target_module', 'N/A')
    folder = session.get('_folder', 'N/A')
    
    print(f"\n📦 Session: {module}")
    print(f"   Folder: {Path(folder).name}")
    
    # Check module_hierarchy
    hierarchy = session.get('module_hierarchy', '')
    print(f"   Hierarchy: {'✓' if hierarchy else '✗'} {hierarchy if hierarchy else '(empty)'}")
    
    # Check conditions (which include inputs and outputs)
    conditions = session.get('conditions', [])
    print(f"   Conditions (MS signals): {len(conditions)}")
    if conditions:
        for c in conditions[:3]:  # Show first 3
            print(f"     - {c.get('name', '?')}: {c.get('expr', '?')[:50]}...")
        if len(conditions) > 3:
            print(f"     ... and {len(conditions)-3} more")
    
    # Check clocks
    clocks = session.get('clocks', [])
    print(f"   Clocks: {len(clocks)}")
    if clocks:
        for c in clocks[:3]:
            print(f"     - {c.get('name', '?')}")
        if len(clocks) > 3:
            print(f"     ... and {len(clocks)-3} more")
    
    # Check resets
    resets = session.get('resets', [])
    print(f"   Resets: {len(resets)}")
    if resets:
        for r in resets[:3]:
            print(f"     - {r.get('name', '?')}")
        if len(resets) > 3:
            print(f"     ... and {len(resets)-3} more")
    
    # Check parameters
    parameters = session.get('parameters', [])
    print(f"   Parameters: {len(parameters)}")
    if parameters:
        for p in parameters[:3]:
            print(f"     - {p.get('name', '?')} = {p.get('default', '?')}")
        if len(parameters) > 3:
            print(f"     ... and {len(parameters)-3} more")

print("\n" + "=" * 70)
