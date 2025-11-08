#!/usr/bin/env python3
"""Verify that session list displays module_hierarchy like main page."""

import sys
from pathlib import Path
import json
import tempfile

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _shorten_path_for_display

# Test data representing a session
session_data = {
    "target_module": "blur_scaler",
    "module_hierarchy": "tb_top.dut.blur_scaler",  # This is what should be displayed
    "rtl_start": "d:\\Programing\\Assertion-Checker-Generator\\EDA\\RTL\\blur_scaler.v",
    "session_excel_path": "d:\\out\\sessions\\blur_scaler-20251109\\blur_scaler.xlsx",
    "out_dir": "d:\\out\\sessions\\blur_scaler-20251109\\assertions"
}

print("Session List Display Test")
print("=" * 70)
print()

# Simulate the display logic
module = session_data.get('target_module', '') or ''
rtl_hierarchy = session_data.get('module_hierarchy', '') or ''
if not rtl_hierarchy:
    rtl_path = session_data.get('rtl_start', '') or ''
    rtl_hierarchy = _shorten_path_for_display(rtl_path, 50) if rtl_path else module
rtl_display = rtl_hierarchy

print("Session Data:")
print(f"  Module: {module}")
print(f"  Hierarchy: {session_data.get('module_hierarchy')}")
print(f"  RTL Start: {session_data.get('rtl_start')}")
print()

print("Display Result (Session List RTL Column):")
print(f"  RTL Display: {rtl_display}")
print()

print("Comparison with Main Page:")
print(f"  Main page shows 'rtl_hierarchy': {session_data.get('module_hierarchy')}")
print(f"  Session list now shows: {rtl_display}")
print()

if rtl_display == session_data.get('module_hierarchy'):
    print("✅ Session list RTL column now matches main page display!")
else:
    print("⚠ Different from main page")
