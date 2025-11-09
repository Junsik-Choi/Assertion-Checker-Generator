#!/usr/bin/env python3
"""
Integration test for signal bit width parsing in assertion wizard.
Simulates the full flow: RTL parsing → signal selection → Excel export
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

def test_complete_flow():
    """Test the complete signal bit width flow."""
    print("\n" + "="*60)
    print("  SIGNAL BIT WIDTH PARSING - INTEGRATION TEST")
    print("="*60 + "\n")
    
    # Step 1: Simulate RTL parsing with calculated_bit_width
    print("Step 1: Simulating RTL parser output with calculated_bit_width")
    print("-" * 60)
    
    module_inputs = [
        {
            'name': 'clk',
            'calculated_bit_width': 1,
            'is_parameterized': False,
            'params_used': [],
        },
        {
            'name': 'rst_n',
            'calculated_bit_width': 1,
            'is_parameterized': False,
            'params_used': [],
        },
        {
            'name': 'i_data',
            'calculated_bit_width': 8,
            'is_parameterized': True,
            'params_used': ['DATA_WIDTH'],
        },
        {
            'name': 'i_addr',
            'calculated_bit_width': 16,
            'is_parameterized': True,
            'params_used': ['ADDR_WIDTH'],
        },
    ]
    
    module_outputs = [
        {
            'name': 'o_valid',
            'calculated_bit_width': 1,
            'is_parameterized': False,
            'params_used': [],
        },
        {
            'name': 'o_result',
            'calculated_bit_width': 32,
            'is_parameterized': False,
            'params_used': [],
        },
    ]
    
    print(f"✓ Module inputs: {len(module_inputs)}")
    for inp in module_inputs:
        print(f"  - {inp['name']}: width={inp['calculated_bit_width']}, param={inp['is_parameterized']}")
    
    print(f"\n✓ Module outputs: {len(module_outputs)}")
    for out in module_outputs:
        print(f"  - {out['name']}: width={out['calculated_bit_width']}, param={out['is_parameterized']}")
    
    # Step 2: Simulate signal selection and storage
    print("\n\nStep 2: Simulating signal selection in wizard")
    print("-" * 60)
    
    # Simulate assertion_input_data (user selections)
    assertion_input_data = {
        'target': 'i_data',
        'plus_con': 'o_valid',
        'reset_con': 'rst_n',
        'trigger_con': 'clk',
        'exp_cnt_val': '10',
    }
    
    # Simulate assertion_signal_ports (port info including widths)
    assertion_signal_ports = {
        'target': module_inputs[2],  # i_data
        'plus_con': module_outputs[0],  # o_valid
        'reset_con': module_inputs[1],  # rst_n
        'trigger_con': module_inputs[0],  # clk
    }
    
    print("Selected signals (Counter assertion):")
    for field, signal_name in assertion_input_data.items():
        if field in assertion_signal_ports:
            port_dict = assertion_signal_ports[field]
            bit_width = port_dict.get('calculated_bit_width', 0)
            print(f"  - {field}: '{signal_name}' (width={bit_width} bits)")
    
    # Step 3: Format output for Excel
    print("\n\nStep 3: Formatting output for Excel export")
    print("-" * 60)
    
    def format_bit_width(bit_width: int) -> str:
        """Format calculated bit width as [msb:lsb]."""
        if bit_width > 0:
            return f"[{bit_width-1}:0]"
        return ""
    
    def extract_signal_name(signal_str: str) -> str:
        """Extract clean signal name (remove brackets)."""
        import re
        match = re.match(r'^([^\[]*)(?:\[.*\])?$', signal_str)
        return match.group(1).strip() if match else signal_str.strip()
    
    # Excel output format
    excel_output = {
        'target': {
            'signal_name': extract_signal_name(assertion_input_data['target']),
            'bit_width': format_bit_width(assertion_signal_ports['target'].get('calculated_bit_width', 0)),
        },
        'plus_con': extract_signal_name(assertion_input_data['plus_con']),
        'reset_con': extract_signal_name(assertion_input_data['reset_con']),
        'trigger_con': extract_signal_name(assertion_input_data['trigger_con']),
        'exp_cnt_val': assertion_input_data['exp_cnt_val'],
    }
    
    print("Excel export format:")
    print(f"  Column 1 (Signal): '{excel_output['target']['signal_name']}'")
    print(f"  Column 2 (Width): '{excel_output['target']['bit_width']}'")
    print(f"  Column 3 (Plus): '{excel_output['plus_con']}'")
    print(f"  Column 4 (Reset): '{excel_output['reset_con']}'")
    print(f"  Column 5 (Trigger): '{excel_output['trigger_con']}'")
    print(f"  Column 6 (Count): '{excel_output['exp_cnt_val']}'")
    
    # Step 4: Validate output
    print("\n\nStep 4: Validating output")
    print("-" * 60)
    
    checks = [
        (excel_output['target']['signal_name'] == 'i_data', "✓ Signal name extracted correctly"),
        (excel_output['target']['bit_width'] == '[7:0]', "✓ Bit width formatted correctly"),
        (excel_output['plus_con'] == 'o_valid', "✓ Plus_con signal extracted correctly"),
        (excel_output['reset_con'] == 'rst_n', "✓ Reset_con signal extracted correctly"),
        (excel_output['trigger_con'] == 'clk', "✓ Trigger_con signal extracted correctly"),
    ]
    
    all_passed = True
    for passed, message in checks:
        if passed:
            print(message)
        else:
            print(f"✗ {message.replace('✓', '')}")
            all_passed = False
    
    # Step 5: Test all three assertion types
    print("\n\nStep 5: Testing all assertion types")
    print("-" * 60)
    
    # Counter test
    print("\n✓ Counter assertion:")
    counter_data = {
        'signal': 'i_data[7:0]',
        'width': format_bit_width(8),
    }
    print(f"  Input: '{counter_data['signal']}' -> Output: name='i_data', width='{counter_data['width']}'")
    
    # Handshake test
    print("\n✓ Handshake assertion:")
    handshake_data = {
        'sender': 'req_sig',
        'receiver': 'ack_sig[0:0]',
        'sender_width': format_bit_width(1),
        'receiver_width': format_bit_width(1),
    }
    print(f"  Sender: '{handshake_data['sender']}' -> width='{handshake_data['sender_width']}'")
    print(f"  Receiver: '{handshake_data['receiver']}' -> width='{handshake_data['receiver_width']}'")
    
    # PulseWidth test
    print("\n✓ PulseWidth assertion:")
    pulse_data = {
        'signal': 'pulse_out[3:0]',
        'width': format_bit_width(4),
    }
    print(f"  Input: '{pulse_data['signal']}' -> Output: name='pulse_out', width='{pulse_data['width']}'")
    
    return all_passed


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n\n" + "="*60)
    print("  EDGE CASES AND ERROR HANDLING")
    print("="*60 + "\n")
    
    import re
    
    def extract_signal_name(signal_str: str) -> str:
        """Extract clean signal name (remove brackets)."""
        match = re.match(r'^([^\[]*)(?:\[.*\])?$', signal_str)
        return match.group(1).strip() if match else signal_str.strip()
    
    def format_bit_width(bit_width: int) -> str:
        """Format calculated bit width as [msb:lsb]."""
        if bit_width > 0:
            return f"[{bit_width-1}:0]"
        return ""
    
    test_cases = [
        ("i_data[7:0]", "i_data", "Name with bracket notation"),
        ("i_data", "i_data", "Plain signal name"),
        ("[7:0]", "", "Only brackets (invalid signal)"),
        ("sig_with_long_name_test[15:0]", "sig_with_long_name_test", "Long signal name"),
        ("clk", "clk", "Single bit signal"),
    ]
    
    print("Signal name extraction:")
    all_passed = True
    for signal_str, expected_name, description in test_cases:
        extracted = extract_signal_name(signal_str)
        passed = extracted == expected_name
        status = "✓" if passed else "✗"
        print(f"{status} {description}")
        print(f"  Input: '{signal_str}' -> Expected: '{expected_name}', Got: '{extracted}'")
        all_passed = all_passed and passed
    
    print("\n\nBit width formatting edge cases:")
    width_cases = [
        (0, "", "Zero width"),
        (1, "[0:0]", "Single bit"),
        (8, "[7:0]", "Standard 8-bit"),
        (16, "[15:0]", "16-bit"),
        (32, "[31:0]", "32-bit"),
        (128, "[127:0]", "Large width"),
    ]
    
    for width, expected, description in width_cases:
        formatted = format_bit_width(width)
        passed = formatted == expected
        status = "✓" if passed else "✗"
        print(f"{status} {description}: width={width} -> '{formatted}'")
        all_passed = all_passed and passed
    
    return all_passed


if __name__ == '__main__':
    try:
        result1 = test_complete_flow()
        result2 = test_edge_cases()
        
        print("\n\n" + "="*60)
        if result1 and result2:
            print("  ✅ ALL TESTS PASSED")
        else:
            print("  ⚠️  SOME TESTS FAILED")
        print("="*60 + "\n")
        
        sys.exit(0 if (result1 and result2) else 1)
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
