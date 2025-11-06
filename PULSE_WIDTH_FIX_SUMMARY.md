# Pulse Width Assertion IndexError Fix (Nov 6, 2025)

## Problem
When attempting to create a pulse width assertion in the TUI, an `IndexError` was raised:

```
IndexError: list index out of range
  File "cli_tui.py", line 4307, in _handle_assertion_wizard_command
    current_field = fields[0]
```

## Root Cause
The `_get_plugin_fields()` function in `cli_tui.py` only had field definitions for 'counter' and 'handshake' plugins, but the codebase also registered 'pulseWidth' and 'delayCondition' plugins.

When users selected these plugins, the function returned an empty list `[]`, causing the wizard to crash when trying to access `fields[0]`.

## Solution
Added field definitions for missing plugins:

### 1. **pulseWidth Plugin Fields** (4 fields)
   - `pulse_type`: Choice between 'hpulse' or 'vpulse'
   - `target_pulse`: Signal whose pulse width to measure
   - `expected_min`: Minimum pulse width in cycles
   - `expected_max`: Maximum pulse width in cycles

### 2. **delayCondition Plugin Fields** (4 fields)
   - `source`: Source signal that triggers delay measurement
   - `target`: Signal that responds after delay
   - `min_delay`: Minimum delay in cycles
   - `max_delay`: Maximum delay in cycles

### 3. **Safety Checks**
   Added defensive checks in `_handle_assertion_wizard_command()` to prevent crashes:
   - Check if fields list is empty before accessing fields[0]
   - Check if current field index is within bounds
   - Return user-friendly error message if fields are not defined

## Files Modified
- `scripts/cli_tui.py` (lines 3450-3550, 4375-4410)
  - `_get_plugin_description()`: Added descriptions for pulseWidth and delayCondition
  - `_get_plugin_fields()`: Added field definitions for pulseWidth and delayCondition
  - `_handle_assertion_wizard_command()`: Added safety checks for empty fields

## Test Results

✅ **All 4 plugins now have field definitions**

```
Registered Plugins: 4
  ✓ delayCondition (4 fields)
  ✓ pulseWidth (4 fields)
  ✓ counter (5 fields)
  ✓ handshake (3 fields)
```

## Verification

### Before Fix
```
Registered Plugins: 4
  ✓ delayCondition (0 fields) → CRASH!
  ✓ pulseWidth (0 fields) → CRASH!
  ✓ counter (5 fields)
  ✓ handshake (3 fields)
```

### After Fix
```
Registered Plugins: 4
  ✓ delayCondition (4 fields) → WORKS!
  ✓ pulseWidth (4 fields) → WORKS!
  ✓ counter (5 fields)
  ✓ handshake (3 fields)
```

## How It Works Now

1. **Select pulseWidth plugin** → User proceeds to step 1 (pulse type selection)
2. **Step 2** → Select target pulse signal
3. **Step 3** → Enter expected minimum pulse width
4. **Step 4** → Enter expected maximum pulse width
5. **Confirmation** → Review configuration and save

Same flow for delayCondition plugin with its 4 steps.

## Breaking Change
None. This is a pure bug fix that adds missing functionality without breaking existing code.

## Future Enhancement
The field definitions could be expanded with:
- Default values for common patterns
- Input validation and range checking
- Pre-filled examples from RTL module ports
- Interactive signal picker for signal-type fields

