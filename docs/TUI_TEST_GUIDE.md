# TUI Manual Test Guide

## Objective
Create a pulse_width assertion for sync_signal.v that verifies i_hsw signal has a pulse width between 10-20 clocks.

## Test Steps

### Step 1: Launch TUI
```powershell
python scripts/cli_tui.py
```

### Step 2: RTL Selection
**Expected:** TUI shows "Step 1/4 - RTL: Enter path to .v or .sv file"

**Action:** Type the following and press Enter:
```
EDA/RTL/sync_signal.v
```

**Expected Result:**
- Status message: "rtl set: D:\Programing\Assertion-Checker-Generator\EDA\RTL\sync_signal.v"
- Progress to Step 2/4

### Step 3: Module/Instance Selection
**Expected:** TUI shows "Step 2/4 - Module: number+Enter"

**Expected Display:**
```
[1] u0_sync_signal
[2] u1_sync_signal
[3] u2_sync_signal
[4] u3_sync_signal
```

**Action:** Type `1` and press Enter to select u0_sync_signal

**Expected Result:**
- Progress to Step 3/4

### Step 4: Hierarchy Selection
**Expected:** TUI shows "Step 3/4 - Hierarchy: Enter/number/custom"

**Action:** Press Enter to accept default hierarchy (u0_sync_signal)

**Expected Result:**
- Progress to Step 4/4

### Step 5: Excel Configuration
**Expected:** TUI shows "Step 4/4 - Excel: path or Enter for default"

**Action:** Press Enter to accept default Excel path

**Expected Result:**
- Onboarding complete
- Dashboard view appears showing:
  - Module: sync_signal
  - Hierarchy: u0_sync_signal
  - Clocks, Resets, Parameters
  - Input/Output ports

### Step 6: Create New Assertion
**Action:** Type `new` and press Enter

**Expected:** Assertion type selection menu appears

**Action:** Select pulse_width assertion type (type number + Enter)

### Step 7: Configure Pulse Width Assertion
**Expected:** Wizard asks for:
1. Signal name
2. Minimum pulse width (clocks)
3. Maximum pulse width (clocks)

**Actions:**
1. Signal: `i_hsw`
2. Min width: `10`
3. Max width: `20`

### Step 8: Verify Assertion Creation
**Expected:**
- Assertion appears in "Created Assertions" panel
- Shows: pulse_width assertion for i_hsw (10-20 clocks)

### Step 9: Generate Files
**Action:** Type `generate` or `gen` and press Enter

**Expected Result:**
- Assertion checker interface file created
- Success message displayed

### Step 10: Verify Output Files
**Action:** Check generated files in output directory

**Expected Files:**
- `sync_signal_pulse_width_intf.sv` (or similar name)
- Contains SystemVerilog assertion checking i_hsw pulse width

## Troubleshooting

### Issue: "ERROR: No instances found"
- Check that sync_signal.v exists in EDA/RTL/
- Verify other RTL files that use sync_signal module exist

### Issue: Instance names not showing
- Check debug log: `out/tui_step1_debug.log`
- Verify find_module_instances_by_file() is being called

### Issue: TUI crashes or shows garbled text
- Check for emoji characters (should all be removed)
- Verify terminal supports UTF-8

## Debug Logs
- Step 1 debug: `out/tui_step1_debug.log`
- General TUI log: Check terminal output

## Success Criteria
✓ Step 2 shows 4 instance names (u0_sync_signal through u3_sync_signal)
✓ Can select an instance and proceed through all 4 steps
✓ Can create pulse_width assertion for i_hsw
✓ Generated assertion file contains correct pulse width check (10-20 clocks)
