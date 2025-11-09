#!/usr/bin/env python3
"""
Test script to verify signal bit width parsing and Excel export.
Tests the infrastructure for extracting signal names and widths from RTL.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

def test_signal_width_parsing():
    """Test the signal width parsing logic."""
    print("\n=== Testing Signal Width Parsing ===\n")
    
    # Test cases
    test_cases = [
        ("i_data[7:0]", "i_data", "[7:0]"),
        ("o_result[15:0]", "o_result", "[15:0]"),
        ("i_addr", "i_addr", ""),
        ("clk", "clk", ""),
        ("rst_n[0:0]", "rst_n", "[0:0]"),
        ("[BUS_WIDTH-1:0]", "", "[BUS_WIDTH-1:0]"),
    ]
    
    import re
    
    def parse_signal_name_and_width(signal_str: str) -> tuple:
        """Parse signal to extract name and width."""
        if not signal_str:
            return "", ""
        
        match = re.match(r'^([^\[]*)\[([^\]]*)\]$', signal_str)
        if match:
            name = match.group(1).strip()
            width = f"[{match.group(2)}]"
            return name, width
        else:
            return signal_str.strip(), ""
    
    for signal_str, expected_name, expected_width in test_cases:
        name, width = parse_signal_name_and_width(signal_str)
        status = "✓" if (name == expected_name and width == expected_width) else "✗"
        print(f"{status} '{signal_str}' -> name='{name}', width='{width}'")
        if name != expected_name or width != expected_width:
            print(f"   Expected: name='{expected_name}', width='{expected_width}'")


def test_bit_width_formatting():
    """Test the bit width formatting logic."""
    print("\n=== Testing Bit Width Formatting ===\n")
    
    def format_bit_width(bit_width: int) -> str:
        """Format calculated bit width as [msb:lsb]."""
        if bit_width > 0:
            return f"[{bit_width-1}:0]"
        return ""
    
    test_cases = [
        (8, "[7:0]"),
        (16, "[15:0]"),
        (1, "[0:0]"),
        (0, ""),
        (32, "[31:0]"),
    ]
    
    for bit_width, expected in test_cases:
        result = format_bit_width(bit_width)
        status = "✓" if result == expected else "✗"
        print(f"{status} bit_width={bit_width} -> '{result}' (expected '{expected}')")


def test_rtl_parser_integration():
    """Test that rtl_parser generates calculated_bit_width."""
    print("\n=== Testing RTL Parser Integration ===\n")
    
    try:
        from rtl_parser import analyze_module_from_verilog
        
        # Create a temporary test Verilog file
        test_verilog = '''
module test_module (
    input clk,
    input rst_n,
    input [7:0] i_data,
    input [15:0] i_addr,
    output [31:0] o_result,
    output [3:0] o_status
);
    // Simple dummy module
endmodule
        '''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.v', delete=False) as f:
            f.write(test_verilog)
            temp_file = f.name
        
        try:
            # Parse the module
            module_info = analyze_module_from_verilog(temp_file, 'test_module', {})
            
            print(f"Module parsed: {module_info.name if module_info else 'Failed'}")
            
            if module_info:
                print(f"\nInputs:")
                for inp in module_info.inputs[:5]:
                    name = inp.get('name', '?')
                    width = inp.get('calculated_bit_width', 0)
                    print(f"  - {name}: calculated_bit_width={width}")
                
                print(f"\nOutputs:")
                for out in module_info.outputs[:5]:
                    name = out.get('name', '?')
                    width = out.get('calculated_bit_width', 0)
                    print(f"  - {name}: calculated_bit_width={width}")
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
        
    except ImportError as e:
        print(f"✗ Could not import rtl_parser: {e}")
    except Exception as e:
        print(f"✗ RTL parser test failed: {e}")


def test_appstate_signal_ports():
    """Test AppState signal_ports storage structure."""
    print("\n=== Testing AppState Signal Ports ===\n")
    
    # Simulate the data structure
    assertion_input_data = {
        'target': 'i_data',
        'plus_con': 'i_valid',
        'reset_con': 'rst_n',
    }
    
    assertion_signal_ports = {
        'target': {
            'name': 'i_data',
            'calculated_bit_width': 8,
            'is_parameterized': False,
            'params_used': [],
        },
        'plus_con': {
            'name': 'i_valid',
            'calculated_bit_width': 1,
            'is_parameterized': False,
            'params_used': [],
        },
        'reset_con': {
            'name': 'rst_n',
            'calculated_bit_width': 1,
            'is_parameterized': False,
            'params_used': [],
        },
    }
    
    print("Assertion input data:")
    for field, value in assertion_input_data.items():
        port_dict = assertion_signal_ports.get(field, {})
        bit_width = port_dict.get('calculated_bit_width', 0)
        width_str = f"[{bit_width-1}:0]" if bit_width > 0 else ""
        print(f"  {field}: '{value}' -> width='{width_str}'")


if __name__ == '__main__':
    test_signal_width_parsing()
    test_bit_width_formatting()
    test_appstate_signal_ports()
    test_rtl_parser_integration()
    
    print("\n=== All Tests Complete ===\n")
