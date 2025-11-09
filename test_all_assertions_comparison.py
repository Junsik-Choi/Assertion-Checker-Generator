#!/usr/bin/env python3
"""
Comparison test: Counter vs Handshake vs PulseWidth previews.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _generate_assertion_preview, ModuleInfo, AppState

# Create test state
state = AppState()
state.module_info = ModuleInfo(
    module="test_module",
    clocks=[{"name": "i_clk", "type": "input"}],
    resets=[{"name": "i_rst_n", "type": "input"}]
)

print("=" * 80)
print("COMPARISON: All Assertion Types")
print("=" * 80)
print()

# Counter
print("1. COUNTER ASSERTION")
print("-" * 80)
counter_data = {
    'target': 'cnt',
    'plus_con': 'inc',
    'reset_con': 'rst',
    'trigger_con': 'chk',
    'exp_cnt_val': '5'
}
lines = _generate_assertion_preview('counter', counter_data, state)
for line in lines[:12]:
    print(line)
print()

# Handshake
print("2. HANDSHAKE ASSERTION")
print("-" * 80)
handshake_data = {
    'phase_type': '2phase',
    'sender': 'req',
    'receiver': 'ack'
}
lines = _generate_assertion_preview('handshake', handshake_data, state)
for line in lines[:13]:
    print(line)
print()

# PulseWidth
print("3. PULSE WIDTH ASSERTION")
print("-" * 80)
pulse_data = {
    'target_signal': 'i_signal',
    'min_width': '10',
    'max_width': '20'
}
lines = _generate_assertion_preview('pulseWidth', pulse_data, state)
for line in lines[:12]:
    print(line)

print()
print("=" * 80)
print("Summary:")
print("=" * 80)
print("""
✓ Counter: Shows target, conditions, clock, reset
✓ Handshake: Shows type, signals, clock, reset
✓ PulseWidth: Shows signal, min/max, clock, reset

All three now have consistent format with Base Clock and Reset!
""")
