# Error Fix Summary: IndexError in Assertion Wizard

## Original Error

```
IndexError: list index out of range
File "d:\Programing\Assertion-Checker-Generator\scripts\cli_tui.py", line 4648, in _handle_assertion_wizard_command
    current_field = fields[0]
                    ~~~~~~^^^
```

## Root Cause

The `pulseWidth` assertion plugin had no fields defined in the `_get_plugin_fields()` function. When a user tried to select this plugin type, the code attempted to access `fields[0]` on an empty list, causing an IndexError.

### Problematic Code Pattern

```python
'pulseWidth': [
    # Empty list!
],
```

Result when trying to access fields:
```
fields = selected['fields']  # Gets empty list []
current_field = fields[0]     # IndexError!
```

## Solution Implemented

### 1. **Added pulseWidth Fields Definition**

Added complete field definitions for the `pulseWidth` assertion type:

```python
'pulseWidth': [
    {
        'name': 'target_signal',
        'type': 'signal',
        'step': 1,
        'title': 'Pulse Signal',
        'description': 'Select the signal to monitor for pulse width',
        'example': 'Select from available signals',
        'required': True,
    },
    {
        'name': 'min_width',
        'type': 'string',
        'step': 2,
        'title': 'Minimum Pulse Width (clocks)',
        'description': 'Enter minimum allowed pulse width in clock cycles',
        'example': '10',
        'required': True,
    },
    {
        'name': 'max_width',
        'type': 'string',
        'step': 3,
        'title': 'Maximum Pulse Width (clocks)',
        'description': 'Enter maximum allowed pulse width in clock cycles',
        'example': '20',
        'required': True,
    },
],
```

### 2. **Added Defensive Programming Checks**

Added safety checks in `_handle_assertion_wizard_command()`:

**Location 1: Type Selection Stage (Line ~4647)**
```python
fields = selected.get('fields', [])
if not fields:
    return f"No fields defined for {selected['name']}", True
current_field = fields[0]
```

**Location 2: Input Data Stage (Line ~4667)**
```python
fields = plugin.get('fields', [])
if not fields or state.assertion_current_field_idx >= len(fields):
    return "No fields or invalid field index", True

current_field = fields[state.assertion_current_field_idx]
```

### 3. **Added Description for pulseWidth**

Updated `_get_plugin_description()`:
```python
descriptions = {
    'counter': '...',
    'handshake': '...',
    'sequence': '...',
    'pulseWidth': 'Verify pulse width constraints within min/max clock cycle range',  # NEW
}
```

## Changes Made

| File | Function | Change |
|------|----------|--------|
| `scripts/cli_tui.py` | `_get_plugin_fields()` | Added `pulseWidth` fields (3 fields) |
| `scripts/cli_tui.py` | `_get_plugin_description()` | Added `pulseWidth` description |
| `scripts/cli_tui.py` | `_handle_assertion_wizard_command()` | Added safety checks for empty fields |

## Test Results

### Before Fix
```
pulseWidth: 0 fields ❌ EMPTY - This would cause IndexError!
```

### After Fix
```
1. counter: 5 fields ✅ OK
2. handshake: 3 fields ✅ OK
3. pulseWidth: 3 fields ✅ OK
```

### Test Cases Passed
✅ Select counter type (fields[0] access safe)
✅ Select handshake type (fields[0] access safe)
✅ Select pulseWidth type (fields[0] access safe)
✅ Enter field data for each type
✅ Navigate between fields (prev/next)

## Impact Analysis

### Direct Impact
- **Fixes**: IndexError when selecting pulseWidth assertion type
- **Enables**: Complete pulseWidth assertion workflow
- **Safety**: Defensive checks prevent similar errors in future

### Backward Compatibility
✅ No breaking changes
✅ Existing assertions (counter, handshake) unaffected
✅ Additional safety checks are non-intrusive

## Files Modified

1. **scripts/cli_tui.py**
   - Line 3851: Added `pulseWidth` to `_get_plugin_description()`
   - Lines 3909-3933: Added complete `pulseWidth` field definitions
   - Lines 4647-4651: Added defensive check in type selection stage
   - Lines 4667-4670: Added defensive check in input data stage

## Verification

Run the following tests to verify the fix:

```bash
# Test 1: Verify all plugins have fields
python test_verify_fix.py
# Expected: All plugins have fields ✅

# Test 2: Test wizard command handling
python test_wizard_command.py
# Expected: All tests passed!

# Test 3: Verify plugin loading
python test_plugins.py
# Expected: pulseWidth has 3 fields
```

## Error Prevention

To prevent similar errors in the future:

1. ✅ **Always populate plugin field definitions** - Empty lists will now be caught
2. ✅ **Use defensive programming** - Added `.get()` and length checks
3. ✅ **Add assertions during setup** - Verify fields are non-empty
4. ✅ **Test all code paths** - Include tests for all plugin types

## Conclusion

The error has been fixed by:
1. Adding complete field definitions for the `pulseWidth` plugin
2. Adding defensive checks to prevent IndexError on empty field lists
3. Verifying all plugins are properly configured

The assertion wizard now properly supports all three assertion types and handles edge cases gracefully.
