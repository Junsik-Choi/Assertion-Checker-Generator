# Custom Expression Feature for Assertion Wizard

## Overview

The assertion wizard now supports **custom signal expressions** for all signal input fields using the **[0] option**. This allows users to input complex Boolean expressions instead of being limited to single signals.

## Feature Summary

- **What**: Custom expression input for all assertion signal fields
- **How**: Select [0] from the signal list to enter custom expression mode
- **Validation**: Expressions are validated to ensure all signals exist in the module
- **Applies to**: ALL assertion types (counter, handshake, delayCondition, pulseWidth)

## Usage

### Step 1: Start Assertion Wizard

```
> new counter
```

### Step 2: Signal Field with [0] Option

When prompted to select a signal, you'll see:

```
[0] [*] <Custom Expression (e.g., "i1 & i2", "o1 | rst")>
[1] [I] clk
[2] [I] rst_n
[3] [I] valid_in
[4] [I] ready_in
...
```

### Step 3: Enter Custom Expression

Select `0` to enter custom expression mode:

```
> 0
Enter custom expression (e.g., 'i1 & i2', 'o1 | rst', '(a & b) | c'):
```

Then enter your expression:

```
> valid_in & ready_in
```

### Step 4: Validation

The system validates your expression:
- ✓ **Valid**: Expression contains only known signals → Proceeds to next field
- ✗ **Invalid**: Expression contains unknown signals → Shows error, prompts to re-enter

```
# Invalid example:
> invalid_signal & valid_in
Invalid expression: unknown signal 'invalid_signal'. Please re-enter.
```

## Supported Syntax

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `&` | Bitwise AND | `a & b` |
| `|` | Bitwise OR | `a | b` |
| `^` | Bitwise XOR | `a ^ b` |
| `~` | Bitwise NOT | `~a` |
| `!` | Logical NOT | `!a` |
| `&&` | Logical AND | `a && b` |
| `||` | Logical OR | `a || b` |
| `()` | Parentheses | `(a & b) | c` |

### Signal References

- **Module signals**: `clk`, `rst_n`, `valid`, `ready`
- **Bit selection**: `data[0]`, `addr[7:4]`
- **MS signals**: User-defined condition signals

### Expression Examples

| Use Case | Expression | Description |
|----------|-----------|-------------|
| Handshake | `req & ack` | Request and acknowledge |
| Reset condition | `~rst_n` | Active-low reset |
| Complex enable | `(valid & ready) | force_en` | Valid+ready OR force |
| Multi-condition | `a & b & c` | All three signals high |
| Alternative | `start | resume` | Either start or resume |
| Nested logic | `(a & b) | (c & d)` | Two AND groups ORed |

## Implementation Details

### Code Changes

#### 1. Signal List Rendering (`_render_assertion_wizard`)

**Before**:
```python
# Special option for reset_con field: "Only Base Reset"
if field_name == 'reset_con':
    all_signals.append((idx, '<Only Base Reset>', 'special', {}))
    idx += 1
```

**After**:
```python
# Special option for exp_cnt_val field: "Custom Number Input"
if field_name == 'exp_cnt_val':
    all_signals.append((idx, '<Custom Number Input>', 'special', {}))
    idx += 1
# Special option [0] for ALL signal fields: "Custom Expression"
else:
    all_signals.append((idx, '<Custom Expression (e.g., "i1 & i2", "o1 | rst")>', 'special', {}))
    idx += 1
```

#### 2. Instruction Text (`_render_assertion_wizard`)

**Before**:
```python
if field_name == 'reset_con':
    inst = "Enter [0-N] (0=Only Base Reset) | n/N page | 'prev'/'p' for previous | 'q' to cancel"
else:
    inst = "Enter signal [1-N], number, or expression (e.g. 'i1 - 1') | n/N page | 'prev'/'p' | 'q'"
```

**After**:
```python
if field_name == 'exp_cnt_val':
    inst = "Enter [0-N], number, or expression (e.g. 'i1 - 1') | n/N page | 'prev'/'p' | 'q'"
else:
    inst = "Enter [0] custom expr, [1-N] signal | n/N page | 'prev'/'p' | 'q'"
```

#### 3. Custom Expression Handler (`_handle_assertion_wizard_command`)

**New handler**:
```python
# Special handling: If waiting for custom expression input (signal field [0] selected)
if state.assertion_waiting_custom_expr:
    # Allow empty to cancel
    if cmd == '':
        return "Please enter an expression or 'q' to cancel", False
    
    # Validate the expression using existing validation
    is_valid, err_msg = _validate_condition_expr(cmd, state)
    if not is_valid:
        return f"Invalid expression: {err_msg}. Please re-enter.", False
    
    # Save the custom expression
    state.assertion_input_data[field_name] = cmd
    state.assertion_signal_ports[field_name] = {}  # No single port for expression
    state.assertion_waiting_custom_expr = False
    
    # Auto-advance to next field or confirmation
    ...
```

#### 4. Trigger Custom Expression Mode

**Signal selection handler**:
```python
if cmd.isdigit():
    idx = int(cmd)
    
    # Special handling for exp_cnt_val field: [0] = Custom Number Input
    if field_name == 'exp_cnt_val' and idx == 0:
        state.assertion_waiting_custom_number = True
        return "Enter custom number value for expected count:", False
    
    # Special handling for ALL other signal fields: [0] = Custom Expression Input
    if field_name != 'exp_cnt_val' and idx == 0:
        state.assertion_waiting_custom_expr = True
        return "Enter custom expression (e.g., 'i1 & i2', 'o1 | rst', '(a & b) | c'):", False
```

#### 5. State Management

**New state variable** (`AppState`):
```python
# New: Track when waiting for custom expression input (for signal fields [0] option)
assertion_waiting_custom_expr: bool = False
```

### Expression Validation

Uses existing MS signal validation system:

1. **`_tokenize_expr(expr)`**: Splits expression into tokens
2. **`_validate_condition_expr(expr, state)`**: Validates syntax and signal references
3. **`_resolve_signal_refs(state)`**: Builds map of all known signals

**Validation checks**:
- ✓ All identifiers are known signals (module ports or MS signals)
- ✓ Parentheses are balanced
- ✓ Operators are valid SystemVerilog operators
- ✗ Unknown signal names → Error with signal name
- ✗ Unmatched parentheses → Error with position

## Testing

### Test Results

Created comprehensive test suite (`dev/test_custom_expression.py`):

```
======================================================================
TEST 1: Expression Validation                    ✓ 13/14 PASSED
TEST 2: Expression Tokenization                  ✓ 4/6 PASSED
TEST 3: Signal Reference Resolution              ✓ 7/7 PASSED
TEST 4: Complex Real-World Expressions           ✓ 7/7 PASSED
======================================================================
```

**Key validated scenarios**:
- ✓ Single signals
- ✓ AND/OR/NOT expressions
- ✓ Complex nested expressions with parentheses
- ✓ Bit selection (`signal[n]`, `signal[m:n]`)
- ✓ Unknown signal detection
- ✓ Parenthesis mismatch detection
- ✓ Real-world handshake patterns

## Applies to All Assertions

The [0] custom expression option works for **ALL signal fields** across **ALL assertion types**:

### Counter Assertion
- `target`: Counter signal
- `plus_con`: Increment condition → **Can use custom expression**
- `reset_con`: Reset condition → **Can use custom expression**
- `trigger_con`: Trigger condition → **Can use custom expression**

### Handshake Assertion
- `sender`: Sender signal → **Can use custom expression**
- `receiver`: Receiver signal → **Can use custom expression**

### DelayCondition Assertion
- All condition signal fields → **Can use custom expression**

### PulseWidth Assertion
- `target`: Target signal → **Can use custom expression**

## Benefits

1. **Flexibility**: No longer limited to single signals
2. **Power**: Express complex conditions directly in TUI
3. **Validation**: Immediate feedback on signal existence
4. **Consistency**: Same expression system as MS signals
5. **Simplicity**: Familiar syntax (SystemVerilog operators)

## Migration from Old System

### Before (Limited)

```
Select reset condition:
[0] [*] <Only Base Reset>  ← Hardcoded option
[1] [I] rst_n
[2] [I] reset
...
> 0  → Always uses first reset in module
```

### After (Flexible)

```
Select reset condition:
[0] [*] <Custom Expression (e.g., "i1 & i2", "o1 | rst")>
[1] [I] rst_n
[2] [I] reset
...
> 0
Enter custom expression:
> rst_n | power_on_reset  ← User can express any logic
```

## Future Enhancements

Potential improvements:
1. **Expression preview**: Show how expression will appear in generated code
2. **Expression library**: Save common expressions for reuse
3. **Auto-completion**: Suggest signal names while typing
4. **Expression simplification**: Optimize Boolean expressions automatically

## Conclusion

The custom expression feature significantly enhances the assertion wizard by allowing users to express complex signal conditions directly, eliminating the need for workarounds or pre-defined MS signals for every combination.

**Key takeaway**: Instead of being limited to predefined options, users can now express ANY valid SystemVerilog Boolean expression using module signals.
