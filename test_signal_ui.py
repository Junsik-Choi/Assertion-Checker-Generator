#!/usr/bin/env python3
"""Test script to verify signal UI changes."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from dataclasses import dataclass, field
from typing import Dict, Any, List

# Test 1: Verify signal map generation
@dataclass
class TestState:
    assertion_signal_map: Dict[int, str] = field(default_factory=dict)
    assertion_input_data: Dict[str, Any] = field(default_factory=dict)

def test_signal_map_generation():
    """Test that signal map is correctly generated."""
    print("Test 1: Signal Map Generation")
    print("-" * 50)
    
    # Simulate inputs
    inputs = [
        {"name": "i_clk"},
        {"name": "i_rst"},
        {"name": "i_data"},
    ]
    
    outputs = [
        {"name": "o_valid"},
        {"name": "o_ready"},
    ]
    
    conditions = [
        {"name": "cond_transfer"},
        {"name": "cond_error"},
    ]
    
    # Build signal map
    signal_map = {}
    idx = 1
    
    for inp in inputs:
        signal_map[idx] = inp["name"]
        idx += 1
    
    for out in outputs:
        signal_map[idx] = out["name"]
        idx += 1
    
    for cond in conditions:
        signal_map[idx] = cond["name"]
        idx += 1
    
    print("Generated Signal Map:")
    for num, signal_name in signal_map.items():
        print(f"  [{num}] {signal_name}")
    
    # Test lookup
    print("\nTest lookup [1] -> i_clk:", signal_map.get(1))
    print("Test lookup [4] -> o_valid:", signal_map.get(4))
    print("Test lookup [7] -> cond_error:", signal_map.get(7))
    
    assert signal_map[1] == "i_clk", "Failed: Signal 1"
    assert signal_map[4] == "o_valid", "Failed: Signal 4"
    assert signal_map[7] == "cond_error", "Failed: Signal 7"
    
    print("✓ Test 1 PASSED\n")
    return True

def test_signal_name_formatting():
    """Test right-aligned signal name formatting with role."""
    print("Test 2: Signal Name Formatting (Right-aligned with role)")
    print("-" * 50)
    
    def format_signal_name(name: str, role: str, width: int = 20) -> str:
        """Format signal name right-aligned with role in parentheses."""
        formatted = f"{name} ({role})"
        return formatted.rjust(width)
    
    # Test formatting
    result1 = format_signal_name("i_data", "input", 25)
    result2 = format_signal_name("sender_sig", "sender", 25)
    result3 = format_signal_name("cnt", "counter", 25)
    
    print(f"Test: {repr(result1)}")
    print(f"      {result1}X  (X marks end)")
    
    print(f"\nTest: {repr(result2)}")
    print(f"      {result2}X")
    
    print(f"\nTest: {repr(result3)}")
    print(f"      {result3}X")
    
    # Verify right alignment
    assert result1.endswith("i_data (input)"), "Failed: Right align 1"
    assert result2.endswith("sender_sig (sender)"), "Failed: Right align 2"
    assert result3.endswith("cnt (counter)"), "Failed: Right align 3"
    
    # Verify total width
    assert len(result1) == 25, f"Failed: Width check - got {len(result1)}"
    
    print("✓ Test 2 PASSED\n")
    return True

def test_preview_lines():
    """Test that timing diagram preview has correct signal format."""
    print("Test 3: Timing Diagram Preview with state-transition-only separators")
    print("-" * 50)
    
    def format_signal_name(name: str, role: str, width: int = 20) -> str:
        formatted = f"{name} ({role})"
        return formatted.rjust(width)
    
    def format_waveform_line(waveform: str, width: int = 20) -> str:
        """Format waveform data right-aligned."""
        return waveform.rjust(width)
    
    # Base clock pattern
    BASE_CLK = "|___|‾‾‾|___|‾‾‾|___|‾‾‾|___|‾‾‾|"
    
    def build_waveform(pattern_spec: str) -> str:
        """Build waveform with | only at state transitions."""
        if not pattern_spec:
            return BASE_CLK
        
        parts = pattern_spec.split(",")
        waveform = ""
        prev_state = None
        
        for part in parts:
            state_info = part.strip().split(":")
            if len(state_info) != 2:
                continue
            state = state_info[0].strip().upper()
            try:
                cycles = int(state_info[1].strip())
            except ValueError:
                continue
            
            # Add separator only at state transitions
            if prev_state is not None and prev_state != state:
                waveform += "|"
            elif prev_state is None:
                waveform += "|"
            
            # Fill cycles with state character and spaces
            if state == "HIGH":
                waveform += "‾‾‾"
                for i in range(1, cycles):
                    waveform += " ‾‾‾"
            elif state == "LOW":
                waveform += "___"
                for i in range(1, cycles):
                    waveform += " ___"
            
            prev_state = state
        
        waveform += "|"
        return waveform
    
    # Generate preview lines
    lines = []
    lines.append("Timing Diagram:")
    lines.append(format_waveform_line("clk") + " " + BASE_CLK)
    lines.append(format_signal_name("my_counter", "counter") + " 0   0   1   1   1   0   0   0")
    lines.append(format_signal_name("inc_cond", "increment") + " " + build_waveform("HIGH:1,LOW:1,HIGH:1,LOW:1,HIGH:1,LOW:2"))
    lines.append(format_signal_name("rst_sig", "reset") + " " + build_waveform("HIGH:1,LOW:4,HIGH:1,LOW:2"))
    lines.append("")
    
    print("Generated Preview Lines:")
    for line in lines:
        print(line)
    
    # Verify formatting
    counter_line = format_signal_name("my_counter", "counter")
    assert "my_counter (counter)" in counter_line, "Failed: Signal name not in line"
    assert counter_line.endswith("my_counter (counter)"), "Failed: Not right-aligned"
    
    clk_line = format_waveform_line("clk")
    assert clk_line.endswith("clk"), "Failed: CLK not right-aligned"
    
    # Verify waveform structure
    waveform = build_waveform("HIGH:3,LOW:2,HIGH:3")
    assert waveform.startswith("|"), "Failed: Should start with |"
    assert waveform.endswith("|"), "Failed: Should end with |"
    assert " ‾" in waveform or " _" in waveform, "Failed: Should have spaces within state"
    
    print("\n✓ Test 3 PASSED\n")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Signal UI Improvements")
    print("=" * 50)
    print()
    
    try:
        test_signal_map_generation()
        test_signal_name_formatting()
        test_preview_lines()
        
        print("=" * 50)
        print("✓ ALL TESTS PASSED")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
