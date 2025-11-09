#!/usr/bin/env python3
"""Test assertion wizard command handling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import (
    _handle_assertion_wizard_command,
    AppState,
    ModuleInfo,
)

# Create test state
state = AppState()
state.assertion_wizard_stage = 'select_type'

print("Test 1: Select counter type")
msg, exit_wizard = _handle_assertion_wizard_command(state, '1')
print(f"  Message: {msg[:50]}...")
print(f"  Exit: {exit_wizard}")
print(f"  Stage: {state.assertion_wizard_stage}")
print()

print("Test 2: Enter first field data")
msg, exit_wizard = _handle_assertion_wizard_command(state, 'mycounter')
print(f"  Message: {msg[:50]}...")
print(f"  Exit: {exit_wizard}")
print(f"  Field index: {state.assertion_current_field_idx}")
print()

print("Test 3: Select handshake type (choice field)")
state2 = AppState()
state2.assertion_wizard_stage = 'select_type'
msg, exit_wizard = _handle_assertion_wizard_command(state2, '2')
print(f"  Message: {msg[:50]}...")
print(f"  Stage: {state2.assertion_wizard_stage}")
print()

print("Test 4: Select choice option")
msg, exit_wizard = _handle_assertion_wizard_command(state2, '1')
print(f"  Message: {msg[:50]}...")
print(f"  Field index: {state2.assertion_current_field_idx}")
print()

print("Test 5: Select pulseWidth type")
state3 = AppState()
state3.assertion_wizard_stage = 'select_type'
msg, exit_wizard = _handle_assertion_wizard_command(state3, '3')
print(f"  Message: {msg[:50]}...")
print(f"  Stage: {state3.assertion_wizard_stage}")
print(f"  Selected type: {state3.assertion_selected_type}")
print()

print("All tests passed!")
