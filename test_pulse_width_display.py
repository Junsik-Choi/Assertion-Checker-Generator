#!/usr/bin/env python3
"""
Test script to verify PulseWidth assertion preview display.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _generate_assertion_preview, ModuleInfo, AppState

# Create test state with module info
state = AppState()
state.module_info = ModuleInfo(
    module="sync_signal",
    module_hierarchy="tb_top.dut.u0_sync_signal",
    clocks=[
        {"name": "i_clk", "type": "input"},
    ],
    resets=[
        {"name": "i_rst_n", "type": "input"},
    ]
)

# Test PulseWidth assertion preview
print("=" * 80)
print("TEST: PulseWidth Assertion Preview")
print("=" * 80)
print()

pulse_width_data = {
    'target_signal': 'i_signal',
    'min_width': '10',
    'max_width': '20'
}

preview_lines = _generate_assertion_preview('pulseWidth', pulse_width_data, state)

print("PulseWidth Assertion Preview:")
print("-" * 80)
for line in preview_lines:
    print(line)

print()
print("=" * 80)
print("Verification:")
print("=" * 80)
print()

# Check that all required info is present
required_info = [
    "PULSE WIDTH ASSERTION",
    "Signal to Monitor: i_signal",
    "Minimum Pulse Width: 10 clocks",
    "Maximum Pulse Width: 20 clocks",
    "Base Clock: i_clk",
    "Base Reset: i_rst_n",
    "Pass Condition",
    "Fail Condition"
]

output_text = "\n".join(preview_lines)
all_present = True

for info in required_info:
    if info in output_text:
        print(f"✓ {info}")
    else:
        print(f"✗ MISSING: {info}")
        all_present = False

print()
if all_present:
    print("✅ All required information is displayed!")
else:
    print("❌ Some information is missing!")
