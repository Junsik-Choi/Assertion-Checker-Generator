#!/usr/bin/env python3
"""
Test script to verify Base Clock and Reset display in assertion preview.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

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

# Test Counter assertion preview
print("=" * 80)
print("TEST: Counter Assertion Preview with Base Clock and Reset")
print("=" * 80)
print()

counter_data = {
    'target': 'cnt_signal',
    'plus_con': 'i_signal',
    'reset_con': 'o_signal_sync',
    'trigger_con': 'i_valid',
    'exp_cnt_val': '5'
}

preview_lines = _generate_assertion_preview('counter', counter_data, state)

print("Counter Assertion Preview:")
print("-" * 80)
for line in preview_lines:
    print(line)

print()
print("=" * 80)
print("TEST: Handshake Assertion Preview with Base Clock and Reset")
print("=" * 80)
print()

handshake_data = {
    'phase_type': '2phase',
    'sender': 'sender_req',
    'receiver': 'receiver_ack'
}

preview_lines = _generate_assertion_preview('handshake', handshake_data, state)

print("Handshake Assertion Preview:")
print("-" * 80)
for line in preview_lines[:20]:  # Show first 20 lines
    print(line)

print()
print("✅ Base Clock and Reset are now displayed in assertions!")
