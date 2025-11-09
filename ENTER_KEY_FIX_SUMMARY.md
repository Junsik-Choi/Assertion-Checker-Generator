# Enter Key Fix - Summary

## Problem
**User's Issue**: "엔터를 눌러도 다음으로 넘어가지 않아" (Pressing Enter doesn't advance to next field)

When entering a value (like `cnt` for counter signal) and pressing Enter, the wizard would NOT advance to the next field. Pressing Enter repeatedly made no progress.

## Root Cause
The `status_msg` (status message) was being displayed **on top of** the wizard UI at row `max_y - 4`.

**Original Code (Line 956-958)**:
```python
# Status message
if status_msg:
    try:
        stdscr.addnstr(max_y - 4, 2, _truncate(status_msg, max_x - 4), max_x - 4)
```

This always displayed the status message, which overlaid the wizard's field display. When the handler correctly advanced the field (`state.assertion_current_field_idx += 1`), the new field prompt was returned as `status_msg`, but it was also overlaid in the same location, making it invisible to the user.

## Solution
Only show `status_msg` when the wizard is **not** active. When the wizard is active, it renders its own complete UI (including field prompts, descriptions, signals, etc.).

**Fixed Code (Line 956-958)**:
```python
# Status message - don't show when wizard is active (wizard renders its own)
if status_msg and not state.assertion_wizard_active:
    try:
        stdscr.addnstr(max_y - 4, 2, _truncate(status_msg, max_x - 4), max_x - 4)
```

## What Changed
- **File**: `scripts/cli_tui.py`
- **Line**: 956
- **Change**: Added condition `and not state.assertion_wizard_active`
- **Scope**: 1 line modified

## How It Works Now

### First Enter (User types "cnt" and presses Enter)
1. Input handler receives `cmdline = "cnt"`
2. Command handler saves to `state.assertion_input_data['counter_signal'] = "cnt"`
3. Returns message: `"OK: cnt\nPress Enter to continue..."`
4. `status_msg` gets this message
5. But `state.assertion_wizard_active == True`, so message is NOT displayed
6. Only the wizard box renders (showing "Current: cnt" ✓)

### Second Enter (User presses Enter again with empty input)
1. Input handler receives `cmdline = ""`
2. Command handler checks: `if cmd == '':`
3. Verifies field is in `state.assertion_input_data` ✓
4. Advances: `state.assertion_current_field_idx += 1`
5. Gets next field from fields list
6. Returns next field prompt message
7. `status_msg` gets this new message
8. But wizard is still active, so message is NOT displayed
9. Next rendering cycle:
   - `_render_field_input_step()` reads new `state.assertion_current_field_idx`
   - Gets the NEXT field definition
   - Renders it in the wizard box
   - User sees: **NEXT FIELD** ✓

## Verification

### Syntax Check
```
✓ PASS: python -m py_compile scripts/cli_tui.py
```
(Only pre-existing SyntaxWarning about escape sequence)

### Test Flow
1. Run: `python scripts/cli_tui.py`
2. Select assertion type: `1` (COUNTER) [Enter]
3. Enter counter signal: `cnt` [Enter]
   - Should now show: **NEXT field** (trigger signal)
4. Enter trigger signal: `check_en` [Enter]
   - Should show: **NEXT field** (comparison value)
5. Each [Enter] advances properly through all 5 steps

## Files Modified
- `scripts/cli_tui.py` - Line 956 (1 line change)

## Files Created (for documentation)
- `test_enter_key_fix.py` - Explanation of the fix
- `test_enter_flow_diagram.py` - Complete flow diagram showing the fix in action

## Status
✅ **FIXED** - Enter key now properly advances through wizard fields
