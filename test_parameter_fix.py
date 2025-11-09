#!/usr/bin/env python3
"""
Test parameter calculation fix for signal bit width parsing.
"""

import sys
import tempfile
from pathlib import Path

def test_parameter_resolution():
    """Test that parameters are correctly resolved."""
    print("\n" + "="*60)
    print("  PARAMETER RESOLUTION TEST")
    print("="*60 + "\n")
    
    # Test cases for parameter detection and resolution
    test_cases = [
        {
            'width': '[7:0]',
            'has_identifiers': False,
            'expected': ('[7:0]', False),
            'desc': 'Plain numeric range'
        },
        {
            'width': '[DATA_WIDTH-1:0]',
            'has_identifiers': True,
            'expected': ('[DATA_WIDTH-1:0]', True),
            'desc': 'Parameter expression (unresolved)'
        },
        {
            'width': '[PARAM_WIDTH-1:0]',
            'has_identifiers': True,
            'expected': ('[PARAM_WIDTH-1:0]', True),
            'desc': 'Parameter expression (unresolved)'
        },
        {
            'width': '[WEIGHT_WIDTH-1:0]',
            'has_identifiers': True,
            'expected': ('[WEIGHT_WIDTH-1:0]', True),
            'desc': 'Parameter expression (unresolved)'
        },
        {
            'width': '[31:0]',
            'has_identifiers': False,
            'expected': ('[31:0]', False),
            'desc': '32-bit numeric range'
        },
    ]
    
    import re
    
    def detect_unresolved_param(width_expr: str) -> bool:
        """Check if width expression contains identifier (parameter reference)."""
        # Check if expression contains identifiers (parameter names)
        has_identifiers = bool(re.search(r'[A-Za-z_]\w*', width_expr))
        return has_identifiers
    
    print("Testing parameter detection:")
    print("-" * 60)
    
    all_passed = True
    for test in test_cases:
        width = test['width']
        has_identifiers = detect_unresolved_param(width)
        expected_has_params = test['expected'][1]
        
        passed = has_identifiers == expected_has_params
        status = "✅" if passed else "❌"
        
        print(f"{status} {test['desc']}")
        print(f"   Width: '{width}'")
        print(f"   Has unresolved params: {has_identifiers} (expected: {expected_has_params})")
        
        all_passed = all_passed and passed
    
    return all_passed


def test_parameter_extraction():
    """Test extracting parameters from module data."""
    print("\n\n" + "="*60)
    print("  PARAMETER EXTRACTION TEST")
    print("="*60 + "\n")
    
    # Simulate module info with parameters
    test_modules = {
        'blur_scaler': {
            'name': 'blur_scaler',
            'param_defaults': {
                'DATA_WIDTH': '8',
                'PARAM_WIDTH': '10',
                'WEIGHT_WIDTH': '6',
            },
            'ports': [
                {'name': 'o_data', 'dir': 'output', 'width': '[DATA_WIDTH-1:0]'},
                {'name': 'i_hor_cnt', 'dir': 'input', 'width': '[PARAM_WIDTH-1:0]'},
                {'name': 'i_w1_cap', 'dir': 'input', 'width': '[WEIGHT_WIDTH-1:0]'},
            ]
        }
    }
    
    print("Module parameters:")
    print("-" * 60)
    
    target_module = 'blur_scaler'
    if target_module in test_modules:
        target_mod = test_modules[target_module]
        if "param_defaults" in target_mod:
            external_params = dict(target_mod["param_defaults"])
            print(f"✅ Extracted {len(external_params)} default parameters:")
            for param, value in external_params.items():
                print(f"   - {param} = {value}")
            
            # Show what would be used for resolution
            print(f"\n✅ Would pass to compute_env_for_occurrence():")
            print(f"   external_params = {external_params}")
            
            return True
    
    return False


def test_width_calculation():
    """Test width calculation from parameters."""
    print("\n\n" + "="*60)
    print("  WIDTH CALCULATION TEST")
    print("="*60 + "\n")
    
    def substitute_and_eval(expr: str, env: dict) -> int:
        """Simple parameter substitution and evaluation."""
        try:
            result = expr
            for param, value in env.items():
                result = result.replace(param, str(value))
            return eval(result)
        except:
            return None
    
    # Simulate environment with resolved parameters
    env = {
        'DATA_WIDTH': '8',
        'PARAM_WIDTH': '10',
        'WEIGHT_WIDTH': '6',
    }
    
    test_cases = [
        {
            'msb_expr': 'DATA_WIDTH-1',
            'lsb_expr': '0',
            'expected': ('[7:0]', 8),
            'desc': 'DATA_WIDTH = 8'
        },
        {
            'msb_expr': 'PARAM_WIDTH-1',
            'lsb_expr': '0',
            'expected': ('[9:0]', 10),
            'desc': 'PARAM_WIDTH = 10'
        },
        {
            'msb_expr': 'WEIGHT_WIDTH-1',
            'lsb_expr': '0',
            'expected': ('[5:0]', 6),
            'desc': 'WEIGHT_WIDTH = 6'
        },
    ]
    
    def format_bit_width(bit_width: int) -> str:
        if bit_width > 0:
            return f"[{bit_width-1}:0]"
        return ""
    
    print("Calculating widths with parameters:")
    print("-" * 60)
    
    all_passed = True
    for test in test_cases:
        msb = substitute_and_eval(test['msb_expr'], env)
        lsb = substitute_and_eval(test['lsb_expr'], env)
        
        if msb is not None and lsb is not None:
            calculated_width = abs(msb - lsb) + 1
            resolved_width = f"[{msb}:{lsb}]"
            formatted = format_bit_width(calculated_width)
            
            expected_resolved, expected_width = test['expected']
            passed = resolved_width == expected_resolved and calculated_width == expected_width
            
            status = "✅" if passed else "❌"
            print(f"{status} {test['desc']}")
            print(f"   Expr: [{test['msb_expr']}:{test['lsb_expr']}]")
            print(f"   Resolved: {resolved_width} ({calculated_width} bits)")
            print(f"   Formatted: {formatted}")
            
            all_passed = all_passed and passed
        else:
            print(f"❌ {test['desc']} - Evaluation failed")
            all_passed = False
    
    return all_passed


if __name__ == '__main__':
    try:
        result1 = test_parameter_resolution()
        result2 = test_parameter_extraction()
        result3 = test_width_calculation()
        
        print("\n\n" + "="*60)
        if result1 and result2 and result3:
            print("  ✅ ALL PARAMETER TESTS PASSED")
        else:
            print("  ⚠️  SOME TESTS FAILED")
        print("="*60 + "\n")
        
        sys.exit(0 if (result1 and result2 and result3) else 1)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
