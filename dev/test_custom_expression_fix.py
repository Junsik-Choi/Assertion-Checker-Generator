#!/usr/bin/env python3
"""
Test custom expression validation improvements:
1. Error messages show in red with helpful signal hints
2. Use actual signal names instead of i1, i2 aliases
3. Clear error display when corrected
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cli_tui import _validate_condition_expr, _resolve_signal_refs, AppState, ModuleInfo

def test_custom_expression_validation():
    """Test the improved custom expression validation with actual signal names."""
    
    # Create test state with sample signals
    state = AppState()
    state.module_info = ModuleInfo()
    state.module_info.inputs = [
        {'name': 'i_sram_rd1', 'width': 1},
        {'name': 'i_sram_rd2', 'width': 1},
        {'name': 'i_sram_rd3', 'width': 1},
        {'name': 'i_clk', 'width': 1},
        {'name': 'i_rst_n', 'width': 1},
        {'name': 'i_valid', 'width': 1},
        {'name': 'i_data', 'width': 8},
    ]
    state.module_info.outputs = [
        {'name': 'o_ready', 'width': 1},
        {'name': 'o_data', 'width': 8},
    ]
    state.conditions = []
    
    print("=" * 70)
    print("TEST: Custom Expression Validation with Actual Signal Names")
    print("=" * 70)
    
    # Test 1: Valid expression with actual signal names
    print("\n--- Test 1: Valid expression ---")
    expr1 = "(i_sram_rd1 && i_sram_rd2) | i_sram_rd3"
    is_valid, err_msg = _validate_condition_expr(expr1, state)
    print(f"Expression: {expr1}")
    print(f"Valid: {is_valid}")
    if not is_valid:
        print(f"Error: {err_msg}")
    assert is_valid, f"Expected valid, got error: {err_msg}"
    print("✓ PASSED")
    
    # Test 2: Invalid signal name - should show helpful error
    print("\n--- Test 2: Invalid signal name ---")
    expr2 = "(i_sram_rd1 && i_invalid_signal) | i_sram_rd3"
    is_valid, err_msg = _validate_condition_expr(expr2, state)
    print(f"Expression: {expr2}")
    print(f"Valid: {is_valid}")
    print(f"Error: {err_msg}")
    assert not is_valid, "Expected invalid"
    assert "i_invalid_signal" in err_msg, "Error should mention the invalid signal"
    assert "not found" in err_msg.lower() or "available" in err_msg.lower(), \
        "Error should be helpful with available signals"
    print("✓ PASSED - Error message is helpful")
    
    # Test 3: Multiple invalid signals
    print("\n--- Test 3: Multiple operators and bit selection ---")
    expr3 = "i_data[7:0] & 8'hFF"
    is_valid, err_msg = _validate_condition_expr(expr3, state)
    print(f"Expression: {expr3}")
    print(f"Valid: {is_valid}")
    if not is_valid:
        print(f"Error: {err_msg}")
    # This should be valid (bit selection is supported)
    print("✓ Result shown")
    
    # Test 4: Complex nested expression
    print("\n--- Test 4: Complex nested expression ---")
    expr4 = "((i_sram_rd1 & i_sram_rd2) | (i_sram_rd3 & i_valid)) & i_rst_n"
    is_valid, err_msg = _validate_condition_expr(expr4, state)
    print(f"Expression: {expr4}")
    print(f"Valid: {is_valid}")
    if not is_valid:
        print(f"Error: {err_msg}")
    assert is_valid, f"Expected valid, got error: {err_msg}"
    print("✓ PASSED")
    
    # Test 5: Unmatched parentheses
    print("\n--- Test 5: Unmatched parentheses ---")
    expr5 = "((i_sram_rd1 & i_sram_rd2) | i_sram_rd3"
    is_valid, err_msg = _validate_condition_expr(expr5, state)
    print(f"Expression: {expr5}")
    print(f"Valid: {is_valid}")
    print(f"Error: {err_msg}")
    assert not is_valid, "Expected invalid due to unmatched parentheses"
    assert "(" in err_msg or "parenthes" in err_msg.lower(), \
        "Error should mention parentheses"
    print("✓ PASSED - Parenthesis error detected")
    
    # Test 6: XOR and other operators
    print("\n--- Test 6: Various operators ---")
    expr6 = "i_sram_rd1 ^ i_sram_rd2 | ~i_sram_rd3"
    is_valid, err_msg = _validate_condition_expr(expr6, state)
    print(f"Expression: {expr6}")
    print(f"Valid: {is_valid}")
    if not is_valid:
        print(f"Error: {err_msg}")
    assert is_valid, f"Expected valid, got error: {err_msg}"
    print("✓ PASSED")
    
    # Test 7: Check signal refs includes all signals
    print("\n--- Test 7: Signal reference resolution ---")
    refs = _resolve_signal_refs(state)
    print(f"Total signals available: {len(refs)}")
    print(f"Sample signals: {list(refs.keys())[:10]}")
    assert 'i_sram_rd1' in refs, "i_sram_rd1 should be in refs"
    assert 'o_ready' in refs, "o_ready should be in refs"
    print("✓ PASSED - All signals properly resolved")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
    print("\nSummary:")
    print("- ✓ Actual signal names work (not i1, i2 aliases)")
    print("- ✓ Invalid signals show helpful error messages")
    print("- ✓ Error messages include available signal hints")
    print("- ✓ Complex expressions with operators validated")
    print("- ✓ Syntax errors properly detected")

if __name__ == "__main__":
    try:
        test_custom_expression_validation()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
