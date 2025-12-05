#!/usr/bin/env python3
"""
Check if other assertion types (Handshake, PulseWidth) are loaded properly
"""
import sys
import json
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _load_sessions

print("=" * 70)
print("ASSERTION TYPES VERIFICATION")
print("=" * 70)

sessions = _load_sessions()

for session in sessions:
    module = session.get('target_module', 'N/A')
    assertions = session.get('assertions', [])
    
    if not assertions:
        continue
    
    print(f"\n📦 Session: {module}")
    print(f"   Total assertions: {len(assertions)}")
    
    # Group by type
    by_type = {}
    for a in assertions:
        atype = a.get('type', 'unknown')
        if atype not in by_type:
            by_type[atype] = []
        by_type[atype].append(a)
    
    for atype, items in by_type.items():
        print(f"\n   [{atype}] - {len(items)} assertion(s)")
        for i, a in enumerate(items, 1):
            data = a.get('data', {})
            print(f"     {i}. {data}")

print("\n" + "=" * 70)
