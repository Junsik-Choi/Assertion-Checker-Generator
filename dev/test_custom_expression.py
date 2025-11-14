"""
Test Custom Expression Feature for Assertion Wizard

This test validates that the [0] custom expression option works correctly
for all assertion types (counter, handshake, delayCondition, pulseWidth).
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from cli_tui import (
    AppState, ModuleInfo,
    _validate_condition_expr,
    _tokenize_expr,
    _resolve_signal_refs
)


def test_expression_validation():
    """Test that expression validation works with module signals."""
    print("\n" + "="*70)
    print("TEST 1: Expression Validation")
    print("="*70)
    
    # Create mock state with some signals
    state = AppState()
    state.module_info = ModuleInfo(
        module="test_module",
        parameters=[],
        inputs=[
            {"name": "clk", "width": "", "direction": "input"},
            {"name": "rst_n", "width": "", "direction": "input"},
            {"name": "valid_in", "width": "", "direction": "input"},
            {"name": "ready_in", "width": "", "direction": "input"},
            {"name": "data_in", "width": "[7:0]", "direction": "input"},
        ],
        outputs=[
            {"name": "valid_out", "width": "", "direction": "output"},
            {"name": "ready_out", "width": "", "direction": "output"},
            {"name": "data_out", "width": "[7:0]", "direction": "output"},
        ],
        inouts=[],
        clocks=[{"name": "clk"}],
        resets=[{"name": "rst_n"}]
    )
    
    # Test cases: (expression, should_pass, description)
    test_cases = [
        # Valid expressions
        ("valid_in", True, "Single signal"),
        ("valid_in & ready_in", True, "AND expression"),
        ("valid_out | ready_out", True, "OR expression"),
        ("(valid_in & ready_in) | rst_n", True, "Complex expression with parentheses"),
        ("~rst_n", True, "NOT expression"),
        ("valid_in && ready_in", True, "Logical AND"),
        ("valid_out || ready_out", True, "Logical OR"),
        ("data_in[0]", True, "Bit selection"),
        ("data_in[7:4]", True, "Range selection"),
        
        # Invalid expressions
        ("invalid_signal", False, "Unknown signal"),
        ("valid_in & unknown", False, "Unknown signal in expression"),
        ("valid_in &", False, "Incomplete expression"),
        ("(valid_in", False, "Unclosed parenthesis"),
        ("valid_in)", False, "Unmatched closing parenthesis"),
    ]
    
    passed = 0
    failed = 0
    
    for expr, should_pass, desc in test_cases:
        is_valid, err_msg = _validate_condition_expr(expr, state)
        
        if is_valid == should_pass:
            print(f"✓ PASS: {desc}")
            print(f"  Expression: {expr}")
            if not is_valid:
                print(f"  Error (expected): {err_msg}")
            passed += 1
        else:
            print(f"✗ FAIL: {desc}")
            print(f"  Expression: {expr}")
            print(f"  Expected: {'valid' if should_pass else 'invalid'}")
            print(f"  Got: {'valid' if is_valid else 'invalid'}")
            if err_msg:
                print(f"  Error: {err_msg}")
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_tokenization():
    """Test expression tokenization."""
    print("\n" + "="*70)
    print("TEST 2: Expression Tokenization")
    print("="*70)
    
    test_cases = [
        ("a & b", ["a", "&", "b"]),
        ("a&&b", ["a", "&&", "b"]),
        ("(a | b) & c", ["(", "a", "|", "b", ")", "&", "c"]),
        ("~rst_n", ["~", "rst_n"]),
        ("sig[7:0]", ["sig", "[", "7", ":", "0", "]"]),
        ("a << 2", ["a", "<<", "2"]),
    ]
    
    passed = 0
    failed = 0
    
    for expr, expected in test_cases:
        tokens = _tokenize_expr(expr)
        if tokens == expected:
            print(f"✓ PASS: {expr}")
            print(f"  Tokens: {tokens}")
            passed += 1
        else:
            print(f"✗ FAIL: {expr}")
            print(f"  Expected: {expected}")
            print(f"  Got: {tokens}")
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_signal_resolution():
    """Test signal reference resolution."""
    print("\n" + "="*70)
    print("TEST 3: Signal Reference Resolution")
    print("="*70)
    
    # Create mock state
    state = AppState()
    state.module_info = ModuleInfo(
        module="test_module",
        parameters=[],
        inputs=[
            {"name": "clk", "width": "", "direction": "input"},
            {"name": "rst_n", "width": "", "direction": "input"},
        ],
        outputs=[
            {"name": "valid", "width": "", "direction": "output"},
        ],
        inouts=[],
        clocks=[{"name": "clk"}],
        resets=[{"name": "rst_n"}]
    )
    
    # Add a condition signal
    state.conditions = [
        {"name": "ms_signal1", "expr": "clk & rst_n"}
    ]
    
    refs = _resolve_signal_refs(state)
    
    # Check that all signals are present
    expected_signals = ["clk", "rst_n", "valid", "ms_signal1", "1", "2", "3"]
    
    passed = 0
    failed = 0
    
    for sig in expected_signals:
        if sig in refs:
            print(f"✓ PASS: Signal '{sig}' found in references")
            passed += 1
        else:
            print(f"✗ FAIL: Signal '{sig}' NOT found in references")
            failed += 1
    
    print()
    print(f"Results: {passed} passed, {failed} failed")
    print(f"Total signals resolved: {len(refs)}")
    return failed == 0


def test_complex_expressions():
    """Test complex real-world expressions."""
    print("\n" + "="*70)
    print("TEST 4: Complex Real-World Expressions")
    print("="*70)
    
    # Create mock state with realistic signals
    state = AppState()
    state.module_info = ModuleInfo(
        module="test_module",
        parameters=[],
        inputs=[
            {"name": "clk", "width": "", "direction": "input"},
            {"name": "rst_n", "width": "", "direction": "input"},
            {"name": "req", "width": "", "direction": "input"},
            {"name": "ack", "width": "", "direction": "input"},
            {"name": "enable", "width": "", "direction": "input"},
            {"name": "data_valid", "width": "", "direction": "input"},
        ],
        outputs=[
            {"name": "busy", "width": "", "direction": "output"},
            {"name": "done", "width": "", "direction": "output"},
        ],
        inouts=[],
        clocks=[{"name": "clk"}],
        resets=[{"name": "rst_n"}]
    )
    
    # Real-world complex expressions
    test_cases = [
        ("req & ack", True, "Handshake condition"),
        ("req & ~ack", True, "Request without ack"),
        ("(req | enable) & ~busy", True, "Complex start condition"),
        ("rst_n & enable & data_valid", True, "Multiple AND conditions"),
        ("(req & ack) | done", True, "Handshake OR done"),
        ("req & (ack | done)", True, "Request with alternative completion"),
        ("~rst_n | (req & ~busy)", True, "Reset OR request"),
    ]
    
    passed = 0
    failed = 0
    
    for expr, should_pass, desc in test_cases:
        is_valid, err_msg = _validate_condition_expr(expr, state)
        
        if is_valid == should_pass:
            print(f"✓ PASS: {desc}")
            print(f"  Expression: {expr}")
            passed += 1
        else:
            print(f"✗ FAIL: {desc}")
            print(f"  Expression: {expr}")
            print(f"  Expected: {'valid' if should_pass else 'invalid'}")
            print(f"  Got: {'valid' if is_valid else 'invalid'}")
            if err_msg:
                print(f"  Error: {err_msg}")
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("CUSTOM EXPRESSION FEATURE TEST SUITE")
    print("="*70)
    
    all_passed = True
    
    all_passed &= test_expression_validation()
    all_passed &= test_tokenization()
    all_passed &= test_signal_resolution()
    all_passed &= test_complex_expressions()
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
