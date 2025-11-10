# Custom Number Input and Expression Support - Implementation Summary

## Overview
Implemented two major enhancements to the assertion wizard signal input system:
1. **Custom Number Input**: Added [0] option for counter exp_cnt_val field to enter custom numbers
2. **Expression Support**: Allow plain numbers and arithmetic expressions in signal fields

## Date
November 10, 2025

## Changes Made

### 1. Custom Number Input for Counter Expected Value

#### Feature Description
When creating counter assertions, users can now select [0] to enter a custom number instead of being forced to select from the signal list.

#### Implementation

**State Variable Added** (`scripts/cli_tui.py` line ~415):
```python
assertion_waiting_custom_number: bool = False  # Track custom number input mode
```

**Rendering Changes** (`_render_field_input_step()`):
- Added [0] <Custom Number Input> as special option at index 0 for exp_cnt_val field
- Special rendering when `assertion_waiting_custom_number = True`:
  ```
  Step 5/5: Custom Number Input
  Enter a custom number value for the expected count
  Type number and press Enter:
  ```
- Updated instruction message: "Enter [0-N], number, or expression..."

**Input Handling** (`_handle_wizard_input()`):
- When user enters [0] in exp_cnt_val field:
  ```python
  if field_name == 'exp_cnt_val' and idx == 0:
      state.assertion_waiting_custom_number = True
      return "Enter custom number value for expected count:", False
  ```
- When in custom number mode, validate and save the number:
  ```python
  if state.assertion_waiting_custom_number:
      # Validate numeric input
      if not cmd.isdigit() and cmd != '':
          return "Please enter a valid number", False
      # Save and advance
      state.assertion_input_data['exp_cnt_val'] = cmd
      state.assertion_waiting_custom_number = False
  ```

**State Cleanup**:
- Reset flag when wizard cancelled (q) or completed

#### Usage Example
```
Step 5/5: Expected Count Value
[0] [*] <Custom Number Input>
[1] [I] i_en
[2] [I] i_data
...

User enters: 0
→ "Enter custom number value for expected count:"

User enters: 42
→ Saved as exp_cnt_val = "42"
```

---

### 2. Plain Number and Expression Support

#### Feature Description
Signal fields now accept:
- **Plain numbers**: `5`, `100`, `255` (no prefix needed)
- **Expressions**: `i1 - 1`, `o_data + 5`, `(i1 + i2) / 2`
- **Signal references**: Still support `[1]` index or name lookup

#### Implementation

**Signal Input Priority** (`_handle_wizard_input()` lines ~5905-5945):

```python
# 1. Check if expression (contains operators)
is_expression = any(op in cmd for op in ['+', '-', '*', '/', '(', ')'])

# 2. If pure digit
if cmd.isdigit():
    idx = int(cmd)
    
    # Special [0] handling (exp_cnt_val, reset_con)
    if field_name == 'exp_cnt_val' and idx == 0:
        # Trigger custom number input
    
    # Check if signal index exists
    if idx in state.assertion_signal_map and idx < 100:
        # Treat as signal index [1], [2], etc.
        selected_signal, selected_port = state.assertion_signal_map[idx]
    else:
        # Treat as plain number value (large number or not in map)
        selected_signal = cmd
        selected_port = {}

# 3. If expression
elif is_expression:
    # Store expression as-is
    selected_signal = cmd
    selected_port = {}

# 4. Try signal name lookup
else:
    # Match by name, or accept as literal value
```

**Priority Order**:
1. Navigation commands ('n', 'N')
2. Special [0] option (field-specific)
3. Small numbers (<100) in signal_map → signal index
4. Expressions (contains +, -, *, /) → expression
5. Large numbers (≥100) or not in map → plain number
6. Text → signal name lookup
7. Fallback → literal value

#### Updated Instructions
```
exp_cnt_val field:
  "Enter [0-N], number, or expression (e.g. 'i1 - 1') | n/N page | 'prev'/'p' | 'q'"

Other signal fields:
  "Enter signal [1-N], number, or expression (e.g. 'i1 - 1') | n/N page | 'prev'/'p' | 'q'"

reset_con field:
  "Enter [0-N] (0=Only Base Reset) | n/N page | 'prev'/'p' for previous | 'q' to cancel"
```

#### Usage Examples

**Plain Numbers**:
```
Step 5: Expected Count Value
Enter: 5
→ Saved as exp_cnt_val = "5" (no signal, just number)

Enter: 150
→ Saved as "150" (too large to be signal index)
```

**Expressions**:
```
Enter: i1 - 1
→ Saved as "i1 - 1" (expression with signal reference)

Enter: o_data + 10
→ Saved as "o_data + 10"

Enter: (i_width + i_height) * 2
→ Saved as complex expression
```

**Signal Index** (existing behavior):
```
Enter: 1
→ If [1] in signal map: select that signal
→ If not in map: treat as plain number "1"
```

---

## Files Modified

1. **scripts/cli_tui.py** (6715 lines):
   - Added `assertion_waiting_custom_number` state variable (line ~415)
   - Modified `_render_field_input_step()`:
     * Added [0] <Custom Number Input> for exp_cnt_val (lines ~4950-4953)
     * Custom number rendering mode (lines ~4878-4892)
     * Updated instruction messages (lines ~5070-5084)
   - Modified `_handle_wizard_input()`:
     * Custom number input handling (lines ~5734-5766)
     * Enhanced signal input logic (lines ~5905-5945)
     * Expression detection and plain number support
   - Reset flag on wizard cancel/complete (lines ~5720, ~5988)

2. **dev/test_custom_number_and_expressions.py** (270 lines):
   - Comprehensive test suite
   - 5 test sections:
     * Custom number option verification
     * Plain number input logic
     * Expression detection
     * Input priority order
     * Instruction messages

## Benefits

### For Users
1. **Flexibility**: No longer forced to select signals when a simple number is needed
2. **Expressions**: Can specify calculations directly (e.g., "i1 - 1" for "port i1 minus 1")
3. **Clarity**: Plain "5" is obviously a number, not signal index [5]
4. **Power**: Combine signals and numbers in expressions

### Technical Benefits
1. **Backward Compatible**: Existing signal index behavior preserved
2. **Intuitive Priority**: Smart detection based on input format
3. **Clean Storage**: Expressions stored as-is with empty port_dict
4. **Extensible**: Easy to add more operators or validation

## Testing

### Test Results
```
✅ TEST 1 PASSED: Custom Number Input Option
✅ TEST 2 PASSED: Plain Number Input
✅ TEST 3 PASSED: Expression Input
✅ TEST 4 PASSED: Signal Input Priority Order
✅ TEST 5 PASSED: Instruction Messages

🎉 ALL 5 TESTS PASSED
```

### Test Coverage
- Field definition verification
- State variable behavior
- Input parsing logic
- Priority order validation
- Instruction message correctness

## User Testing Steps

1. **Start TUI**:
   ```bash
   python scripts/cli_tui.py
   ```

2. **Create Counter Assertion** (Main page → 'n' → '1'):
   - Progress through steps 1-4 normally

3. **Test Custom Number Input** (Step 5):
   ```
   Step 5/5: Expected Count Value
   [0] <Custom Number Input>  ← SELECT THIS
   [1] i_signal1
   [2] i_signal2
   ...
   
   Enter: 0
   → "Enter custom number value for expected count:"
   
   Enter: 42
   → Saved as exp_cnt_val = "42"
   ```

4. **Test Plain Numbers**:
   ```
   Enter: 5
   → Saved as "5" (plain number)
   
   Enter: 100
   → Saved as "100"
   ```

5. **Test Expressions**:
   ```
   Enter: i1 - 1
   → Saved as "i1 - 1" (expression)
   
   Enter: o_data + 5
   → Saved as "o_data + 5"
   ```

6. **Verify Excel Write/Read**:
   - Complete assertion creation
   - Check Excel file (Counter sheet, Column F)
   - Close and reopen session to verify persistence

## Known Limitations

1. **Expression Validation**: Expressions are not validated at input time
   - Stored as-is, validation happens during code generation
   - Invalid expressions will cause errors during assertion file generation

2. **Number vs Index Ambiguity**: Small numbers (1-99) are checked against signal_map first
   - If signal [5] exists, "5" selects the signal
   - To force number "5", use expression like "5 + 0" or select [0] for custom input

3. **Operator Detection**: Only detects common operators: `+`, `-`, `*`, `/`, `(`, `)`
   - Uncommon operators (e.g., `%`, `&`, `|`) treated as signal names

## Future Enhancements

1. **Expression Validation**: Add syntax checking at input time
2. **Preview**: Show evaluated expression result in preview panel
3. **Auto-Complete**: Suggest signal names during expression typing
4. **Help**: Show available operators and example expressions

## Related Documentation

- `docs/ONLY_BASE_RESET_FEATURE.md` - Similar [0] option pattern for reset_con
- `docs/PULSEWIDTH_IMPROVEMENTS.md` - Conditional field logic used here
- `docs/PARAMETER_FIX_SUMMARY.md` - Parameter input support (similar concept)

## Conclusion

Both features successfully implemented and tested:
- ✅ Custom number input with [0] option
- ✅ Plain number and expression support
- ✅ All automated tests passing
- ✅ Ready for user testing in TUI

The implementation maintains backward compatibility while adding powerful new input modes for assertion creation.
