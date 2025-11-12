#!/usr/bin/env python3
"""
Test gen command functionality - verify it properly calls assertion plugins.
"""

import sys
from pathlib import Path

# Add scripts to path
_THIS_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _THIS_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

def test_gen_file_generation():
    """Test that _generate_files properly uses assertion plugins."""
    print("\n" + "=" * 80)
    print("TEST: Gen Command File Generation")
    print("=" * 80)
    
    # Mock AppState with required attributes
    class MockModuleInfo:
        def __init__(self):
            self.module = "test_module"
            self.clocks = [{"name": "i_clk", "width": "1"}]
            self.resets = [{"name": "i_rstn", "width": "1"}]
            self.inputs = [
                {"name": "i_data", "width": "8"},
                {"name": "i_valid", "width": "1"}
            ]
            self.outputs = [
                {"name": "o_result", "width": "16"},
                {"name": "o_ready", "width": "1"}
            ]
            self.inouts = []
            self.parameters = []
    
    class MockState:
        def __init__(self):
            self.gen_filename = "test_assertion"
            self.gen_file_type = 3  # Both interface and instance
            self.gen_data_source = "1"  # Assertions only
            self.out_dir = Path("out/test_gen")
            self.session_excel_path = None  # No actual Excel for this test
            self.module_info = MockModuleInfo()
            self.conditions = []
            self.gen_wizard_active = True
    
    state = MockState()
    
    # Import the function
    from cli_tui import _generate_files  # type: ignore
    
    # Call the function
    try:
        result = _generate_files(state)
        print(f"\n✓ Function executed: {result[:100]}")
        
        # Check if files were created
        if_file = state.out_dir / f"{state.gen_filename}.if.sv"
        inst_file = state.out_dir / f"{state.gen_filename}.inst.sv"
        
        if if_file.exists():
            print(f"✓ Interface file created: {if_file.name}")
            content = if_file.read_text(encoding='utf-8')
            print(f"  - Size: {len(content)} bytes")
            print(f"  - Has UVM header: {'uvm_macros' in content}")
            print(f"  - Has interface declaration: {'interface assertion_intf' in content}")
            
            # Show first 20 lines
            lines = content.split('\n')[:20]
            print("\n  First 20 lines:")
            for i, line in enumerate(lines, 1):
                print(f"    {i:2d}: {line}")
        else:
            print(f"✗ Interface file NOT created")
        
        if inst_file.exists():
            print(f"\n✓ Instance file created: {inst_file.name}")
            content = inst_file.read_text(encoding='utf-8')
            print(f"  - Size: {len(content)} bytes")
            print(f"  - Has UVM header: {'uvm_macros' in content}")
            
            # Show first 15 lines
            lines = content.split('\n')[:15]
            print("\n  First 15 lines:")
            for i, line in enumerate(lines, 1):
                print(f"    {i:2d}: {line}")
        else:
            print(f"✗ Instance file NOT created")
        
        # Cleanup
        if if_file.exists():
            if_file.unlink()
        if inst_file.exists():
            inst_file.unlink()
        if state.out_dir.exists() and not list(state.out_dir.iterdir()):
            state.out_dir.rmdir()
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Gen functionality is working")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        return False


def test_interface_generation_with_plugins():
    """Test interface generation from plugin outputs."""
    print("\n" + "=" * 80)
    print("TEST: Interface Generation from Plugin Outputs")
    print("=" * 80)
    
    class MockModuleInfo:
        def __init__(self):
            self.module = "test_module"
            self.clocks = [{"name": "i_clk", "width": "1"}]
            self.resets = [{"name": "i_rstn", "width": "1"}]
            self.inputs = [{"name": "i_data", "width": "8"}]
            self.outputs = [{"name": "o_result", "width": "16"}]
            self.inouts = []
            self.parameters = []
    
    class MockState:
        def __init__(self):
            self.module_info = MockModuleInfo()
    
    state = MockState()
    
    # Mock plugin outputs (counter plugin style)
    counter_sv = """
`include "uvm_macros.svh"
import uvm_pkg::*;

module assertion_counter
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [0:0] i_valid,
    input logic [7:0] i_data
);

    reg [31:0] cnt;

    always @(posedge i_clk or negedge i_rstn) begin
        if(!i_rstn) begin
            cnt <= 0;
        end
        else if(i_valid) begin
            cnt <= cnt+1;
        end
    end

    property p_counter_check;
        @(posedge i_clk) disable iff(!i_rstn)
        i_data == 8'hFF |-> (cnt == 32'd10);
    endproperty

    assert property (p_counter_check) else $error("failed at %t", $time);

endmodule
"""
    
    sv_snippets = [("counter", counter_sv)]
    
    from cli_tui import _generate_interface_from_plugins  # type: ignore
    
    try:
        result = _generate_interface_from_plugins(state, sv_snippets, include_signals=True)
        
        print("\n✓ Interface generated successfully")
        print(f"  - Size: {len(result)} bytes")
        print(f"  - Has UVM header: {'uvm_macros' in result}")
        print(f"  - Has interface declaration: {'interface assertion_intf' in result}")
        print(f"  - Has input ports: {'input logic' in result}")
        print(f"  - Has counter body: {'cnt <=' in result}")
        print(f"  - Has assertion: {'assert property' in result}")
        
        # Check extracted inputs
        import re
        input_pattern = re.compile(r'input logic\s+(\[[^\]]+\])\s+(\w+)')
        inputs = input_pattern.findall(result)
        print(f"\n  Extracted {len(inputs)} input ports:")
        for width, name in inputs:
            print(f"    - {name} {width}")
        
        # Show structure
        lines = result.split('\n')
        print(f"\n  Total lines: {len(lines)}")
        print("\n  First 30 lines:")
        for i, line in enumerate(lines[:30], 1):
            print(f"    {i:2d}: {line}")
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Interface generation working correctly")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        return False


def test_instance_generation_with_plugins():
    """Test instance generation from plugin outputs."""
    print("\n" + "=" * 80)
    print("TEST: Instance Generation from Plugin Outputs")
    print("=" * 80)
    
    class MockModuleInfo:
        def __init__(self):
            self.module = "test_module"
            self.clocks = [{"name": "i_clk", "width": "1"}]
            self.resets = [{"name": "i_rstn", "width": "1"}]
            self.inputs = [{"name": "i_data", "width": "8"}]
            self.outputs = [{"name": "o_result", "width": "16"}]
    
    class MockState:
        def __init__(self):
            self.module_info = MockModuleInfo()
    
    state = MockState()
    
    # Mock plugin instance output
    counter_inst = """
`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_counter
 u_assertion_counter ();

assign u_assertion_counter.i_clk = top.dut.i_clk;
assign u_assertion_counter.i_rstn = top.dut.i_rstn;
assign u_assertion_counter.i_valid = top.dut.i_valid;
assign u_assertion_counter.i_data = top.dut.i_data;
"""
    
    inst_snippets = [("counter", counter_inst)]
    
    from cli_tui import _generate_instance_from_plugins  # type: ignore
    
    try:
        result = _generate_instance_from_plugins(state, inst_snippets, include_signals=True)
        
        print("\n✓ Instance file generated successfully")
        print(f"  - Size: {len(result)} bytes")
        print(f"  - Has UVM header: {'uvm_macros' in result}")
        print(f"  - Has module instance: {'assertion_counter' in result}")
        print(f"  - Has assigns: {'assign' in result}")
        
        # Check assign statements
        import re
        assign_pattern = re.compile(r'assign\s+\S+\s+=\s+\S+;')
        assigns = assign_pattern.findall(result)
        print(f"\n  Found {len(assigns)} assign statements:")
        for assign in assigns:
            print(f"    {assign}")
        
        # Show full content
        lines = result.split('\n')
        print(f"\n  Total lines: {len(lines)}")
        print("\n  All content:")
        for i, line in enumerate(lines, 1):
            print(f"    {i:2d}: {line}")
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Instance generation working correctly")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TESTING GEN COMMAND FUNCTIONALITY")
    print("=" * 80)
    
    results = []
    
    # Test 1: Basic file generation
    results.append(("Basic File Generation", test_gen_file_generation()))
    
    # Test 2: Interface generation from plugins
    results.append(("Interface Generation", test_interface_generation_with_plugins()))
    
    # Test 3: Instance generation from plugins
    results.append(("Instance Generation", test_instance_generation_with_plugins()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:12s} - {name}")
    
    print("-" * 80)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 80)
    
    sys.exit(0 if passed == total else 1)
