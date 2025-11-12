# MS Signal Enhancement - Prefix Detection & Operator Highlighting

## Overview
Enhanced MS signal creation with clear prefix-based port type detection and comprehensive Verilog operator syntax highlighting.

## Date
November 11, 2025

## Changes Made

### 1. Prefix-Based Signal Type Detection

#### Problem
Previously, plain numbers (1, 2, 3) were automatically mapped to input ports, which was confusing:
- `ms sig = 1 + 2` would map "1" to input[0] and "2" to input[1]
- No clear way to specify which port type (input/output/parameter/etc.)
- Plain numbers couldn't be used as literal values

#### Solution
Implemented clear prefix system for port type specification:

| Prefix | Maps To | Example | Result |
|--------|---------|---------|--------|
| **i1, i2, i3** | Input ports | `ms sig = i1 + i2` | inputs[0] + inputs[1] |
| **o1, o2** | Output ports | `ms sig = o1 * 2` | outputs[0] * 2 |
| **p1, p2** | Parameters | `ms sig = p1 > 10` | parameters[0] > 10 |
| **c1, c2** | Clocks | `ms sig = c1` | clocks[0] |
| **r1, r2** | Resets | `ms sig = r1` | resets[0] |
| **1, 2, 3** | Literal numbers | `ms sig = i1 + 1` | inputs[0] + 1 |

#### Code Changes

**File**: `scripts/cli_tui.py` (lines ~2791-2804)

**Before**:
```python
# Plain number: map to input (backward compatibility)
if token.isdigit():
    idx = int(token)
    ins = (state.module_info.inputs + state.module_info.inouts)
    if 1 <= idx <= len(ins):
        return ins[idx-1].get('name', '')

return token
```

**After**:
```python
# Plain numbers (1, 2, 3, etc.) remain as literal numbers
# No automatic mapping to input ports
# Users must use i1, i2, etc. for input ports

return token
```

This simple change prevents plain numbers from being automatically mapped, requiring explicit prefixes for port references.

### 2. Comprehensive Verilog Operator Highlighting

#### Problem
Only basic operators were highlighted:
- Logical: `&&`, `||`, `!`
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Bitwise: `&`, `|`, `^`, `~`

Missing operators:
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `**`
- Shift: `<<`, `>>`, `<<<`, `>>>`

#### Solution
Extended operator list to cover all Verilog operators with blue/cyan highlighting.

**File**: `scripts/cli_tui.py` (lines ~703-723)

**Before**:
```python
# Operators: &&, ||, &, |, ^, ~, !, ==, !=, <, >, <=, >=
operators = ["&&", "||", "==", "!=", "<=", ">=", "&", "|", "^", "~", "!", "<", ">"]
```

**After**:
```python
# Verilog operators (sorted by length, longest first for proper matching)
# Logical: &&, ||, ==, !=, <=, >=, <, >, !
# Bitwise: &, |, ^, ~
# Arithmetic: +, -, *, /, %, **
# Shift: <<, >>, <<<, >>>
operators = [
    "<<<", ">>>",  # Arithmetic shifts (3 chars)
    "**", "&&", "||", "==", "!=", "<=", ">=", "<<", ">>",  # 2 chars
    "&", "|", "^", "~", "!", "<", ">", "+", "-", "*", "/", "%"  # 1 char
]
```

**Key Points**:
- **23 operators total** (previously 13)
- **Sorted by length** (longest first) for proper matching
- **All Verilog operators** covered

## Usage Examples

### Prefix-Based Port Selection

```bash
# Create MS signals using prefixes

# Input ports (i1, i2, i3...)
> ms sum = i1 + i2 + 1
✓ Condition added: sum (8bits)
  → Maps: inputs[0] + inputs[1] + 1

> ms data_shifted = i3 << 2
✓ Condition added: data_shifted (8bits)
  → Maps: inputs[2] << 2

# Output ports (o1, o2...)
> ms output_doubled = o1 * 2
✓ Condition added: output_doubled (8bits)
  → Maps: outputs[0] * 2

# Parameters (p1, p2...)
> ms threshold_check = i1 > p1
✓ Condition added: threshold_check (1bits)
  → Maps: inputs[0] > parameters[0]

# Clocks (c1, c2...)
> ms clock_gate = c1 && enable
✓ Condition added: clock_gate (1bits)
  → Maps: clocks[0] && enable

# Resets (r1, r2...)
> ms reset_combo = r1 || r2
✓ Condition added: reset_combo (1bits)
  → Maps: resets[0] || resets[1]

# Mixed with literal numbers
> ms result = (i1 + 5) * 3 - o1
✓ Condition added: result (8bits)
  → Uses literal numbers 5 and 3
```

### Operator Highlighting in TUI

When viewing Conditions page ('c' command), expressions are displayed with syntax highlighting:

```
Conditions (MS Signals):
─────────────────────────────────────────────────
[1] sum (8bits)
    i_clk + i_reset + 1
          ^         ^     ← Blue/cyan operators

[2] shifted (8bits)
    i_data << 2
           ^^          ← Blue/cyan shift operator

[3] logic (1bits)
    i_clk && i_reset || i_data
          ^^         ^^       ← Blue/cyan logical operators

[4] complex (8bits)
    (i1 + 2) * (o1 - 1) / 3
        ^    ^     ^    ^      ← All arithmetic operators in blue
```

### Comparison: Before vs After

#### Before (Confusing)
```bash
> ms sig = 1 + 2
  → Maps to: inputs[0] + inputs[1]  ❌ Unexpected!
  
> ms sig2 = 3 * 4
  → Maps to: inputs[2] * inputs[3]  ❌ Not what we meant!

Expression: i_clk + i_reset
            Highlighting: (no + operator highlighted)
```

#### After (Clear)
```bash
> ms sig = 1 + 2
  → Uses literals: 1 + 2  ✓ Exactly what we want!
  
> ms sig2 = i1 + i2
  → Maps to: inputs[0] + inputs[1]  ✓ Clear with prefix!

> ms sig3 = 3 * 4
  → Uses literals: 3 * 4  ✓ Numbers stay as numbers!

Expression: i_clk + i_reset
            Highlighting: +  ← Blue/cyan operator ✓
```

## Benefits

### 1. Clear Intent
- **i1** = clearly an input port
- **1** = clearly a literal number
- No ambiguity or confusion

### 2. Type Safety
- Can't accidentally use numbers as port references
- Must explicitly choose port type (input/output/param/etc.)

### 3. Better Readability
- Prefix indicates port type at a glance
- Operators highlighted for easy visual parsing

### 4. Flexibility
- Mix ports and literals freely: `i1 + 5 * 3`
- Use any Verilog operator: `i1 << 2 | o1 >> 1`

### 5. Visual Feedback
- All operators highlighted in blue/cyan
- Easy to spot arithmetic vs logical operations
- Nested expressions easier to read

## Operator Categories

### Arithmetic (Blue/Cyan)
- `+` Addition
- `-` Subtraction
- `*` Multiplication
- `/` Division
- `%` Modulo
- `**` Power

### Shift (Blue/Cyan)
- `<<` Logical left shift
- `>>` Logical right shift
- `<<<` Arithmetic left shift
- `>>>` Arithmetic right shift

### Comparison (Blue/Cyan)
- `<` Less than
- `>` Greater than
- `<=` Less or equal
- `>=` Greater or equal
- `==` Equal
- `!=` Not equal

### Logical (Blue/Cyan)
- `&&` Logical AND
- `||` Logical OR
- `!` Logical NOT

### Bitwise (Blue/Cyan)
- `&` Bitwise AND
- `|` Bitwise OR
- `^` Bitwise XOR
- `~` Bitwise NOT

## Testing

### Test Results
```
✅ TEST 1 PASSED: Prefix-Based Signal Type Detection
✅ TEST 2 PASSED: Verilog Operator Highlighting
✅ TEST 3 PASSED: Combined Usage
✅ TEST 4 PASSED: Edge Cases

🎉 ALL 4 TESTS PASSED
```

### Test Coverage
- All prefix types (i/o/p/c/r)
- Plain numbers remain as literals
- All 23 Verilog operators highlighted
- Complex expressions
- Edge cases (large numbers, out of range, no spaces)

## Migration Guide

### Old Syntax (Still Works)
```bash
# Direct signal names still work
> ms sig = i_clk + i_reset
✓ Uses actual signal names

# Prefix notation for clarity
> ms sig2 = i1 + i2
✓ Maps to first two inputs
```

### Recommended New Syntax
```bash
# Use prefixes for port references
ms sum = i1 + i2          # inputs[0] + inputs[1]
ms prod = o1 * p1         # outputs[0] * parameters[0]
ms shift = i3 << 2        # inputs[2] << 2

# Use plain numbers for literals
ms calc = i1 + 10         # inputs[0] + 10 (literal)
ms mult = o1 * 2          # outputs[0] * 2 (literal)

# Mix freely
ms complex = (i1 + 5) * 3 - o1 / 2
```

## Files Modified

1. **scripts/cli_tui.py**:
   - Lines 2791-2804: Removed plain number → input mapping
   - Lines 703-723: Extended operator list for highlighting

2. **dev/test_ms_signal_enhancements.py** (283 lines):
   - Comprehensive test suite
   - 4 test sections covering all features
   - All tests passing

3. **docs/MS_SIGNAL_ENHANCEMENTS.md**:
   - Complete documentation (this file)

## Known Limitations

1. **Index Range**: Prefixes only work within available port counts
   - `i100` won't map if only 3 inputs exist
   - Out of range indices treated as literal tokens

2. **Zero Index**: `i0`, `o0` etc. are not valid
   - Port indices start at 1 (i1, o1, etc.)

3. **Negative Indices**: Not supported
   - `i-1` will be parsed as `i` and `-1` separately

## Future Enhancements

1. **Auto-Complete**: Suggest prefixes while typing
2. **Hover Info**: Show actual signal name for prefix
3. **Range Check**: Warn if prefix index out of range
4. **Syntax Error**: Highlight invalid prefix usage

## Related Features

- MS signal validation (existing)
- Expression bit width inference (existing)
- Cycle detection (existing)
- Define sheet auto-update (existing)

## Conclusion

Successfully implemented two major enhancements:
- ✅ Clear prefix-based port type detection (i/o/p/c/r)
- ✅ Comprehensive Verilog operator highlighting (23 operators)
- ✅ Plain numbers remain as literals (no auto-mapping)
- ✅ All automated tests passing

The features provide clearer syntax, better visual feedback, and prevent common errors when creating MS signals.
