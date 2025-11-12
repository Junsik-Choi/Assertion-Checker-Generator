#!/usr/bin/env python3
"""
Test gen command with updated assertion plugins (delayCondition, pulseWidth).
"""

import sys
from pathlib import Path

# Add scripts to path
_THIS_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _THIS_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def test_delaycondition_parsing():
    """Test that delayCondition plugin output is properly parsed."""
    print("\n" + "=" * 80)
    print("TEST: DelayCondition Plugin Compatibility")
    print("=" * 80)
    
    # Mock delayCondition output (multiple sets)
    delay_sv = """
`include "uvm_macros.svh"
import uvm_pkg::*;

module assertion_delayCondition
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [0:0] i_trigger1,
    input logic [0:0] i_result1,
    input logic [0:0] i_trigger2,
    input logic [0:0] i_result2
);

property p_delayCondition_check1(trigger, result);
    @(posedge i_clk) disable iff(!i_rstn)
    $rose(trigger) |-> ##[1 : 5] $rose(result);
endproperty

assert property (p_delayCondition_check1(i_trigger1, i_result1)) else $error("failed at %t", $time);

property p_delayCondition_check2(trigger, result);
    @(posedge i_clk) disable iff(!i_rstn)
    $rose(trigger) |-> ##[2 : 10] $rose(result);
endproperty

assert property (p_delayCondition_check2(i_trigger2, i_result2)) else $error("failed at %t", $time);

endmodule
"""
    
    delay_inst = """
`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_delayCondition u_assertion_delayCondition();

assign u_assertion_delayCondition.i_clk = top.dut.i_clk;
assign u_assertion_delayCondition.i_rstn = top.dut.i_rstn;
assign u_assertion_delayCondition.i_trigger1 = top.dut.i_trigger1;
assign u_assertion_delayCondition.i_result1 = top.dut.i_result1;
assign u_assertion_delayCondition.i_trigger2 = top.dut.i_trigger2;
assign u_assertion_delayCondition.i_result2 = top.dut.i_result2;
"""
    
    class MockModuleInfo:
        def __init__(self):
            self.module = "test_module"
            self.clocks = [{"name": "i_clk", "width": "1"}]
            self.resets = [{"name": "i_rstn", "width": "1"}]
            self.inputs = [
                {"name": "i_trigger1", "width": "1"},
                {"name": "i_result1", "width": "1"},
                {"name": "i_trigger2", "width": "1"},
                {"name": "i_result2", "width": "1"}
            ]
            self.outputs = []
            self.inouts = []
            self.parameters = []
    
    class MockState:
        def __init__(self):
            self.module_info = MockModuleInfo()
    
    state = MockState()
    sv_snippets = [("delayCondition", delay_sv)]
    inst_snippets = [("delayCondition", delay_inst)]
    
    from cli_tui import _generate_interface_from_plugins, _generate_instance_from_plugins  # type: ignore
    
    try:
        # Test interface generation
        iface = _generate_interface_from_plugins(state, sv_snippets, include_signals=False)
        
        print("\n✓ Interface generated")
        print(f"  - Has UVM header: {'uvm_macros' in iface}")
        print(f"  - Has interface: {'interface assertion_intf' in iface}")
        print(f"  - Has properties: {'property p_delayCondition_check' in iface}")
        print(f"  - Property count: {iface.count('property p_delayCondition_check')}")
        
        # Count input ports
        import re
        inputs = re.findall(r'input logic.*?(\w+)', iface)
        print(f"  - Input ports: {len(inputs)} ({', '.join(inputs)})")
        
        # Test instance generation
        inst = _generate_instance_from_plugins(state, inst_snippets, include_signals=False)
        
        print("\n✓ Instance generated")
        print(f"  - Has module: {'assertion_delayCondition' in inst}")
        print(f"  - Assign count: {inst.count('assign')}")
        
        # Verify module extraction
        assert 'u_assertion_delayCondition' in inst
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: DelayCondition plugin compatible")
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


def test_pulsewidth_parsing():
    """Test that pulseWidth plugin outputs are properly parsed."""
    print("\n" + "=" * 80)
    print("TEST: PulseWidth Plugin Compatibility")
    print("=" * 80)
    
    # Mock hpulse output
    hpulse_sv = """
`include "uvm_macros.svh"
import uvm_pkg::*;

module assertion_hpulse
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [7:0] i_signal,
    input logic [3:0] i_min,
    input logic [3:0] i_max
);

property p_hpulse;
    int value_count;
    @(posedge i_clk) disable iff(!i_rstn)
    (i_signal) |-> (1, value_count = 0)
    ##1 (i_signal, value_count = value_count + 1)[*0:$]
    ##1 (!i_signal, value_count = value_count + 1)
    ##0 (i_min <= value_count && value_count <= i_max);
endproperty

assert property (p_hpulse)
    else $error("failed at %t", $time);

endmodule
"""
    
    hpulse_inst = """
`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_hpulse
 u_assertion_hpulse ();

assign u_assertion_hpulse.i_clk = top.dut.i_clk;
assign u_assertion_hpulse.i_rstn = top.dut.i_rstn;
assign u_assertion_hpulse.i_signal = top.dut.i_signal;
assign u_assertion_hpulse.i_min = top.dut.i_min;
assign u_assertion_hpulse.i_max = top.dut.i_max;
"""
    
    # Mock vpulse output
    vpulse_sv = """
`include "uvm_macros.svh"
import uvm_pkg::*;

module assertion_vpulse
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [0:0] i_count_trig,
    input logic [7:0] i_signal,
    input logic [3:0] i_min,
    input logic [3:0] i_max
);

sequence s_vpulse(value_count);
    @(negedge i_count_trig)
    (i_signal, value_count = value_count + 1)[*0:$]
    ##1 (!i_signal);
endsequence

property p_vpulse;
    int value_count;
    @(posedge i_count_trig) disable iff(!i_rstn)
    (i_signal) |-> (1, value_count = 0)
    ##0 s_vpulse(value_count)
    ##1 (i_min <= value_count && value_count <= i_max);
endproperty

assert property (p_vpulse)
    else $error("failed at %t", $time);

endmodule
"""
    
    vpulse_inst = """
`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_vpulse
 u_assertion_vpulse ();

assign u_assertion_vpulse.i_clk = top.dut.i_clk;
assign u_assertion_vpulse.i_rstn = top.dut.i_rstn;
assign u_assertion_vpulse.i_count_trig = top.dut.i_count_trig;
assign u_assertion_vpulse.i_signal = top.dut.i_signal;
assign u_assertion_vpulse.i_min = top.dut.i_min;
assign u_assertion_vpulse.i_max = top.dut.i_max;
"""
    
    class MockModuleInfo:
        def __init__(self):
            self.module = "test_module"
            self.clocks = [{"name": "i_clk", "width": "1"}]
            self.resets = [{"name": "i_rstn", "width": "1"}]
            self.inputs = [
                {"name": "i_signal", "width": "8"},
                {"name": "i_count_trig", "width": "1"},
                {"name": "i_min", "width": "4"},
                {"name": "i_max", "width": "4"}
            ]
            self.outputs = []
    
    class MockState:
        def __init__(self):
            self.module_info = MockModuleInfo()
    
    state = MockState()
    
    from cli_tui import _generate_interface_from_plugins, _generate_instance_from_plugins  # type: ignore
    
    try:
        # Test hpulse
        print("\n--- Testing hpulse ---")
        sv_snippets_h = [("pulseWidth", hpulse_sv)]
        inst_snippets_h = [("pulseWidth", hpulse_inst)]
        
        iface_h = _generate_interface_from_plugins(state, sv_snippets_h, include_signals=False)
        inst_h = _generate_instance_from_plugins(state, inst_snippets_h, include_signals=False)
        
        print("✓ hpulse interface generated")
        print(f"  - Has property: {'property p_hpulse' in iface_h}")
        print(f"  - Has sequence: {'sequence' in iface_h}")  # Should be False for hpulse
        
        print("✓ hpulse instance generated")
        print(f"  - Has module: {'assertion_hpulse' in inst_h}")
        
        # Test vpulse
        print("\n--- Testing vpulse ---")
        sv_snippets_v = [("pulseWidth", vpulse_sv)]
        inst_snippets_v = [("pulseWidth", vpulse_inst)]
        
        iface_v = _generate_interface_from_plugins(state, sv_snippets_v, include_signals=False)
        inst_v = _generate_instance_from_plugins(state, inst_snippets_v, include_signals=False)
        
        print("✓ vpulse interface generated")
        print(f"  - Has property: {'property p_vpulse' in iface_v}")
        print(f"  - Has sequence: {'sequence s_vpulse' in iface_v}")
        
        print("✓ vpulse instance generated")
        print(f"  - Has module: {'assertion_vpulse' in inst_v}")
        
        # Test both together
        print("\n--- Testing combined (hpulse + vpulse) ---")
        sv_snippets_both = [("pulseWidth_h", hpulse_sv), ("pulseWidth_v", vpulse_sv)]
        inst_snippets_both = [("pulseWidth_h", hpulse_inst), ("pulseWidth_v", vpulse_inst)]
        
        iface_both = _generate_interface_from_plugins(state, sv_snippets_both, include_signals=False)
        inst_both = _generate_instance_from_plugins(state, inst_snippets_both, include_signals=False)
        
        print("✓ Combined interface generated")
        print(f"  - Has hpulse property: {'property p_hpulse' in iface_both}")
        print(f"  - Has vpulse property: {'property p_vpulse' in iface_both}")
        
        print("✓ Combined instance generated")
        print(f"  - Has hpulse module: {'assertion_hpulse' in inst_both}")
        print(f"  - Has vpulse module: {'assertion_vpulse' in inst_both}")
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: PulseWidth plugin compatible")
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


def test_mixed_plugins():
    """Test multiple plugins together (counter + handshake + delayCondition + pulseWidth)."""
    print("\n" + "=" * 80)
    print("TEST: Mixed Plugin Compatibility")
    print("=" * 80)
    
    # Simplified outputs from each plugin
    counter_sv = """module assertion_counter(input logic [0:0] i_clk, input logic [0:0] i_rstn); 
reg [31:0] cnt; 
always @(posedge i_clk) begin if(!i_rstn) cnt <= 0; end
endmodule"""
    
    counter_inst = """assertion_counter u_assertion_counter();
assign u_assertion_counter.i_clk = top.dut.i_clk;
assign u_assertion_counter.i_rstn = top.dut.i_rstn;"""
    
    handshake_sv = """module assertion_gen(input logic [0:0] i_clk, input logic [0:0] i_rstn, input logic [0:0] req, input logic [0:0] ack);
property p_2phase_check; @(posedge i_clk) 1; endproperty
endmodule"""
    
    handshake_inst = """assertion_gen u_assertion_gen();
assign u_assertion_gen.i_clk = top.dut.i_clk;
assign u_assertion_gen.req = top.dut.req;
assign u_assertion_gen.ack = top.dut.ack;"""
    
    delay_sv = """module assertion_delayCondition(input logic [0:0] i_clk, input logic [0:0] trig);
property p_check; @(posedge i_clk) 1; endproperty
endmodule"""
    
    delay_inst = """assertion_delayCondition u_assertion_delayCondition();
assign u_assertion_delayCondition.i_clk = top.dut.i_clk;"""
    
    pulse_sv = """module assertion_hpulse(input logic [0:0] i_clk, input logic [7:0] sig);
property p_hpulse; int x; @(posedge i_clk) 1; endproperty
endmodule"""
    
    pulse_inst = """assertion_hpulse u_assertion_hpulse();
assign u_assertion_hpulse.i_clk = top.dut.i_clk;
assign u_assertion_hpulse.sig = top.dut.sig;"""
    
    class MockModuleInfo:
        def __init__(self):
            self.inputs = []
            self.outputs = []
    
    class MockState:
        def __init__(self):
            self.module_info = MockModuleInfo()
    
    state = MockState()
    
    sv_snippets = [
        ("counter", counter_sv),
        ("handshake", handshake_sv),
        ("delayCondition", delay_sv),
        ("pulseWidth", pulse_sv)
    ]
    
    inst_snippets = [
        ("counter", counter_inst),
        ("handshake", handshake_inst),
        ("delayCondition", delay_inst),
        ("pulseWidth", pulse_inst)
    ]
    
    from cli_tui import _generate_interface_from_plugins, _generate_instance_from_plugins  # type: ignore
    
    try:
        iface = _generate_interface_from_plugins(state, sv_snippets, include_signals=False)
        inst = _generate_instance_from_plugins(state, inst_snippets, include_signals=False)
        
        print("\n✓ Mixed interface generated")
        print(f"  - Has counter: {'cnt' in iface}")
        print(f"  - Has handshake: {'p_2phase_check' in iface}")
        print(f"  - Has delayCondition: {'assertion_delayCondition' in iface}")
        print(f"  - Has pulseWidth: {'p_hpulse' in iface}")
        
        print("\n✓ Mixed instance generated")
        modules = ['assertion_counter', 'assertion_gen', 'assertion_delayCondition', 'assertion_hpulse']
        for mod in modules:
            found = mod in inst
            print(f"  - {mod}: {'✓' if found else '✗'}")
            if not found:
                raise AssertionError(f"Module {mod} not found in instance file")
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Mixed plugins compatible")
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
    print("TESTING GEN COMMAND WITH UPDATED PLUGINS")
    print("=" * 80)
    
    results = []
    
    # Test 1: DelayCondition compatibility
    results.append(("DelayCondition Plugin", test_delaycondition_parsing()))
    
    # Test 2: PulseWidth compatibility
    results.append(("PulseWidth Plugin", test_pulsewidth_parsing()))
    
    # Test 3: Mixed plugins
    results.append(("Mixed Plugins", test_mixed_plugins()))
    
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
