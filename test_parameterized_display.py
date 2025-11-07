#!/usr/bin/env python3
"""
Test script to verify parameterized signal display in TUI Step 1.
Shows how port information is displayed with parameter metadata.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from rtl_parser import (
    find_rtl_root_from,
    discover_files,
    build_modules_db,
    find_occurrences_of_target,
    compute_env_for_occurrence,
    resolve_ports_with_params,
)

def test_parameterized_signal_display():
    """Test displaying parameterized signals with metadata."""
    
    rtl_file = Path("d:/Programing/Assertion-Checker-Generator/EDA/RTL/blur_scaler.v")
    
    if not rtl_file.exists():
        print(f"ERROR: RTL file not found: {rtl_file}")
        return False
    
    print("=" * 90)
    print("TEST: Parameterized Signal Display in Module Port List")
    print("=" * 90)
    print(f"RTL File: {rtl_file}")
    print()
    
    # Build modules database
    modules = build_modules_db([rtl_file], allow_unknown=True)
    if not modules:
        print("ERROR: No modules parsed")
        return False
    
    print(f"Modules parsed: {len(modules)}")
    print(f"Available modules: {list(modules.keys())}")
    print()
    
    # Get blur_scaler module
    target = "blur_scaler"
    if target not in modules:
        print(f"ERROR: Module '{target}' not found")
        return False
    
    # Use default parameter values from module definition
    # Since blur_scaler.v is standalone, we use the default parameters
    env = {
        "WEIGHT_WIDTH": "4",
        "DATA_WIDTH": "8",
        "PARAM_WIDTH": "11",
        "SUM_WIDTH": "12"  # WEIGHT_WIDTH + DATA_WIDTH = 4 + 8 = 12
    }
    
    print(f"Environment (parameters): {env}")
    print()
    
    # Resolve ports with parameters
    ports_resolved = resolve_ports_with_params(modules, target, env)
    
    print("=" * 90)
    print("INPUT PORTS (with parameter metadata)")
    print("=" * 90)
    print(f"{'#':<3} {'Name':<25} {'Width':<20} {'Parameterized':<15} {'Bit Width':<12}")
    print("-" * 90)
    
    for idx, port in enumerate(ports_resolved["inputs"], 1):
        name = port.get("name", "?")
        width = port.get("width", "")
        is_param = port.get("is_parameterized", False)
        bit_width = port.get("calculated_bit_width", 0)
        
        param_str = "YES" if is_param else "NO"
        bit_width_str = str(bit_width) if bit_width > 0 else "-"
        
        print(f"{idx:<3} {name:<25} {width:<20} {param_str:<15} {bit_width_str:<12}")
    
    print()
    print("=" * 90)
    print("OUTPUT PORTS (with parameter metadata)")
    print("=" * 90)
    print(f"{'#':<3} {'Name':<25} {'Width':<20} {'Parameterized':<15} {'Bit Width':<12}")
    print("-" * 90)
    
    for idx, port in enumerate(ports_resolved["outputs"], 1):
        name = port.get("name", "?")
        width = port.get("width", "")
        is_param = port.get("is_parameterized", False)
        bit_width = port.get("calculated_bit_width", 0)
        
        param_str = "YES" if is_param else "NO"
        bit_width_str = str(bit_width) if bit_width > 0 else "-"
        
        print(f"{idx:<3} {name:<25} {width:<20} {param_str:<15} {bit_width_str:<12}")
    
    print()
    print("=" * 90)
    print("DETAILED VIEW: Selected Parameterized Input Signals")
    print("=" * 90)
    
    # Show detailed info for parameterized inputs
    param_inputs = [p for p in ports_resolved["inputs"] if p.get("is_parameterized")]
    
    for port in param_inputs:
        print()
        print(f"Signal: {port['name']}")
        print(f"  - Raw Width Expression: {port.get('raw_width', 'N/A')}")
        print(f"  - Resolved Width: {port.get('width', 'N/A')}")
        print(f"  - Parameters Used: {', '.join(port.get('params_used', []))}")
        print(f"  - Calculated Bit Width: {port.get('calculated_bit_width', 0)} bits")
    
    print()
    print("=" * 90)
    print("INFO: Blue color would be applied to parameterized signals in TUI")
    print("=" * 90)
    
    return True


if __name__ == "__main__":
    print("\n\nTesting Parameterized Signal Display\n")
    
    success = test_parameterized_signal_display()
    
    if success:
        print("\n\nTest PASSED!")
        sys.exit(0)
    else:
        print("\n\nTest FAILED!")
        sys.exit(1)
