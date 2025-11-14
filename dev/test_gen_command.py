#!/usr/bin/env python3
"""
Test gen command functions
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cli_tui import (
    _generate_interface_content, 
    _generate_instance_content,
    _generate_preview_content,
    AppState, 
    ModuleInfo
)

def test_preview_functions():
    """Test that preview functions work without errors."""
    print("=" * 70)
    print("TEST: Gen Command Preview Functions")
    print("=" * 70)
    
    # Setup state
    state = AppState()
    state.module_info = ModuleInfo()
    state.module_info.module = "test_module"
    state.module_info.inputs = [
        {'name': 'i_clk', 'width': 1},
        {'name': 'i_valid', 'width': 1},
    ]
    state.module_info.outputs = [
        {'name': 'o_ready', 'width': 1},
    ]
    state.module_info.clocks = [{'name': 'i_clk'}]
    state.module_info.resets = []
    state.module_info.inouts = []
    state.module_info.parameters = []
    state.conditions = []
    
    # Test 1: _generate_interface_content exists
    print("\n--- Test 1: Interface content function exists ---")
    try:
        result = _generate_interface_content(state, include_asserts=False, include_signals=True)
        print(f"✓ Function callable")
        print(f"✓ Result type: {type(result)}")
        print(f"✓ Result length: {len(result)} characters")
        assert isinstance(result, str), "Should return string"
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    
    # Test 2: _generate_instance_content exists
    print("\n--- Test 2: Instance content function exists ---")
    try:
        result = _generate_instance_content(state, include_asserts=False, include_signals=True)
        print(f"✓ Function callable")
        print(f"✓ Result type: {type(result)}")
        print(f"✓ Result length: {len(result)} characters")
        assert isinstance(result, str), "Should return string"
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    
    # Test 3: _generate_preview_content works
    print("\n--- Test 3: Preview content function ---")
    try:
        # Incomplete config
        state.gen_filename = None
        state.gen_file_type = None
        state.gen_data_source = None
        result = _generate_preview_content(state)
        print(f"✓ Handles incomplete config")
        assert isinstance(result, list), "Should return list"
        print(f"✓ Result: {result}")
        
        # Complete config
        state.gen_filename = "test_file"
        state.gen_file_type = 1  # Interface only
        state.gen_data_source = '2'  # Signals only
        state.gen_preview_file_idx = 0
        result = _generate_preview_content(state)
        print(f"✓ Handles complete config")
        assert isinstance(result, list), "Should return list"
        print(f"✓ Result lines: {len(result)}")
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
    print("\nVerified:")
    print("- ✓ _generate_interface_content function works")
    print("- ✓ _generate_instance_content function works")
    print("- ✓ _generate_preview_content function works")
    print("- ✓ No NameError exceptions")


if __name__ == "__main__":
    try:
        test_preview_functions()
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
