#!/usr/bin/env python3
"""
Test script to verify parameterized signal width calculation and tracking.
Tests the new resolve_width_token_with_params() and updated resolve_ports_with_params() functions.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from rtl_parser import (
    resolve_width_token_with_params,
    parse_param_defaults_from_header,
    safe_eval_int,
    substitute_and_eval,
)

def test_parameterized_width_resolution():
    """Test resolving parameterized width expressions."""
    
    print("=" * 70)
    print("TEST: Parameterized Signal Width Resolution")
    print("=" * 70)
    
    # Test cases based on blur_scaler.v
    test_cases = [
        # (width_expr, env, expected_result)
        ("[WEIGHT_WIDTH-1:0]", {"WEIGHT_WIDTH": "4"}, 
         {"is_param": True, "bit_width": 4, "resolved": "[3:0]"}),
        
        ("[PARAM_WIDTH-1:0]", {"PARAM_WIDTH": "11"}, 
         {"is_param": True, "bit_width": 11, "resolved": "[10:0]"}),
        
        ("[DATA_WIDTH-1:0]", {"DATA_WIDTH": "8"}, 
         {"is_param": True, "bit_width": 8, "resolved": "[7:0]"}),
        
        ("[WEIGHT_WIDTH*3-1:0]", {"WEIGHT_WIDTH": "4"}, 
         {"is_param": True, "bit_width": 12, "resolved": "[11:0]"}),
        
        ("[DATA_WIDTH*3-1:0]", {"DATA_WIDTH": "8"}, 
         {"is_param": True, "bit_width": 24, "resolved": "[23:0]"}),
        
        ("[7:0]", {}, 
         {"is_param": False, "bit_width": 8, "resolved": "[7:0]"}),
    ]
    
    passed = 0
    failed = 0
    
    for width_expr, env, expected in test_cases:
        result = resolve_width_token_with_params(width_expr, env)
        
        is_match = (
            result["is_parameterized"] == expected["is_param"] and
            result["calculated_bit_width"] == expected["bit_width"] and
            result["resolved_width"] == expected["resolved"]
        )
        
        status = "PASS" if is_match else "FAIL"
        if is_match:
            passed += 1
        else:
            failed += 1
        
        print(f"\n[{status}] Width Expression: {width_expr}")
        print(f"      Environment: {env}")
        print(f"      Expected: {expected}")
        print(f"      Got:      {result}")
        if not is_match:
            print(f"      Mismatch details:")
            print(f"        - is_parameterized: {result['is_parameterized']} vs {expected['is_param']}")
            print(f"        - calculated_bit_width: {result['calculated_bit_width']} vs {expected['bit_width']}")
            print(f"        - resolved_width: {result['resolved_width']} vs {expected['resolved']}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


def test_parameter_extraction():
    """Test extracting parameter defaults from module headers."""
    
    print("\n" + "=" * 70)
    print("TEST: Parameter Extraction from Module Headers")
    print("=" * 70)
    
    # Test cases
    test_cases = [
        # Module header parameter string
        ("parameter WEIGHT_WIDTH = 4, PARAM_WIDTH = 11, DATA_WIDTH = 8",
         {"WEIGHT_WIDTH": "4", "PARAM_WIDTH": "11", "DATA_WIDTH": "8"}),
        
        ("parameter A = 1, B = 2, C = 3",
         {"A": "1", "B": "2", "C": "3"}),
        
        ("parameter WIDTH = 8",
         {"WIDTH": "8"}),
    ]
    
    passed = 0
    failed = 0
    
    for param_str, expected in test_cases:
        result = parse_param_defaults_from_header(param_str)
        
        is_match = result == expected
        status = "PASS" if is_match else "FAIL"
        if is_match:
            passed += 1
        else:
            failed += 1
        
        print(f"\n[{status}] Parameter String: {param_str}")
        print(f"      Expected: {expected}")
        print(f"      Got:      {result}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


def test_sample_signals():
    """Test with sample signal definitions from blur_scaler.v."""
    
    print("\n" + "=" * 70)
    print("TEST: Sample Signal Definitions (blur_scaler.v)")
    print("=" * 70)
    
    env = {
        "WEIGHT_WIDTH": "4",
        "DATA_WIDTH": "8",
        "PARAM_WIDTH": "11",
    }
    
    # Signals from blur_scaler.v
    signals = [
        ("i_w1_cap", "[WEIGHT_WIDTH-1:0]"),
        ("i_w2_cap", "[WEIGHT_WIDTH-1:0]"),
        ("i_w3_cap", "[WEIGHT_WIDTH-1:0]"),
        ("i_vact_state", "[PARAM_WIDTH-1:0]"),
        ("i_hor_cnt", "[PARAM_WIDTH-1:0]"),
        ("i_sram_rd1", "[DATA_WIDTH-1:0]"),
        ("i_sram_rd2", "[DATA_WIDTH-1:0]"),
        ("i_sram_rd3", "[DATA_WIDTH-1:0]"),
        ("o_data", "[DATA_WIDTH-1:0]"),
        ("r_weight_line1", "[WEIGHT_WIDTH*3-1:0]"),
        ("r_filter_line1", "[DATA_WIDTH*3-1:0]"),
    ]
    
    print(f"\nModule Parameters: {env}\n")
    print(f"{'Signal':<20} {'Width Expr':<20} {'Calculated':<20} {'Params Used':<20}")
    print("-" * 80)
    
    for sig_name, width_expr in signals:
        result = resolve_width_token_with_params(width_expr, env)
        params_str = ",".join(result["params_used"]) if result["params_used"] else "-"
        print(f"{sig_name:<20} {width_expr:<20} {result['resolved_width']:<20} {params_str:<20}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n\nTesting Parameterized Signal Width Resolution\n")
    
    test1_pass = test_parameterized_width_resolution()
    test2_pass = test_parameter_extraction()
    test_sample_signals()
    
    if test1_pass and test2_pass:
        print("\n\nAll tests PASSED!")
        sys.exit(0)
    else:
        print("\n\nSome tests FAILED!")
        sys.exit(1)
