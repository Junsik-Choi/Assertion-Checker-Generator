# Quick TUI Test Guide

## Step-by-Step Instructions

1. Start TUI:
```powershell
python scripts/cli_tui.py
```

2. Step 1: Enter RTL file path
```
EDA/RTL/sync_signal.v
```

3. Step 2: Select instance (try selecting u1_sync_signal)
```
2
```

4. **Step 3: Check what hierarchy is displayed**
   - Should show: `u1_sync_signal` (without full path)
   - Should be in **RED** with warning
   - Should say: "WARNING: Could not find full hierarchy path."
   - Should show: "Please type the full path manually (e.g., top.dut.u1_sync_signal)."

5. **Type custom hierarchy**:
```
IP_BLUR_SCALER_TOP.u1_sync_signal
```

6. Continue to Step 4

## Expected Result

Step 3 should now look like:
```
[DUT Hierarchy Path] - INCOMPLETE  (in RED)
  u1_sync_signal                    (in RED, bold)
WARNING: Could not find full hierarchy path.  (in RED)
Please type the full path manually...  (in RED)

[Alternative Hierarchies]
(none - if state.occs is empty)
```

Then user types the full path and proceeds.
