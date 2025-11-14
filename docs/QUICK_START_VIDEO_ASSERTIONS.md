# Quick Start Guide: Creating Video Timing Assertions

## Available Assertion Types

### Already Supported
1. **counter** - Counter-based assertions
2. **handshake** - Handshake protocol (2-phase/4-phase/ready-valid)
3. **pulseWidth** - Pulse width verification (hpulse/vpulse)
4. **delayCondition** - Delay-based conditions

### NEW: Video Timing Assertions ✨

5. **hact** - Horizontal Active Pixel Count
6. **hsw** - Horizontal Sync Width
7. **hbp** - Horizontal Back Porch
8. **hfp** - Horizontal Front Porch  
9. **vbp** - Vertical Back Porch
10. **vfp** - Vertical Front Porch
11. **vsw** - Vertical Sync Width

---

## Quick Start Commands

### List Available Assertions
```
> new
```
Shows all 11 assertion types with descriptions and status.

### Create Assertion
```
> new hact        # Create Horizontal Active Pixel Count assertion
> new hsw         # Create Horizontal Sync Width assertion
> new hbp         # Create Horizontal Back Porch assertion
...
```

---

## Example: Creating HACT Assertion

```bash
# 1. Start the assertion wizard
> new hact

# Step 1: Select Hsync Signal
# The wizard shows available signals from your module:
[0] [*] <Custom Expression (e.g., "i1 & i2", "o1 | rst")>
[1] [I] i_hsync
[2] [I] i_vsync
[3] [I] i_de
...

# Select hsync signal (option 1)
> 1

# Step 2: Select Data Enable Signal
[0] [*] <Custom Expression>
[1] [I] i_de
[2] [I] i_valid
...

# Select data enable (option 1)
> 1

# Step 3: Enter Expected Min Value
# Enter minimum expected active pixels per line
> 1920

# Step 4: Enter Expected Max Value
# Enter maximum expected active pixels per line
> 1920

# Step 5: Review and Confirm
# The wizard shows:
#   - All your inputs
#   - Preview of the assertion
#   - Timing diagram
#
# Press Enter to create
> [Enter]

# ✅ Assertion created and written to Excel!
```

---

## Field Patterns

All video timing assertions follow similar patterns:

### Pattern 1: Hsync-Based (HACT, HBP, HFP, HSW)
- **Step 1**: Select Hsync Signal
- **Step 2**: Select Data Enable/Target Signal
- **Step 3**: Enter Min Value
- **Step 4**: Enter Max Value

### Pattern 2: Vsync-Based (VBP, VFP)
- **Step 1**: Select Vsync Signal
- **Step 2**: Select Data Enable Signal
- **Step 3**: Enter Min Lines
- **Step 4**: Enter Max Lines

### Pattern 3: Both Syncs (VSW)
- **Step 1**: Select Hsync Signal (for counting)
- **Step 2**: Select Vsync Signal
- **Step 3**: Enter Min Lines
- **Step 4**: Enter Max Lines

---

## Using Custom Expressions

For any signal field, you can use **[0] Custom Expression**:

```bash
# Example: Complex reset condition
Step X: Select Signal
> 0                                    # Select custom expression
Enter expression: 
> i_rst_n & ~i_error_flag             # Use Boolean operators

# Example: Multiple data enable signals
Step X: Select Data Enable
> 0
Enter expression:
> (i_de_ch1 | i_de_ch2) & i_valid     # Complex logic
```

### Supported Operators
- `&` - AND
- `|` - OR  
- `^` - XOR
- `~` - NOT
- `&&` - Logical AND
- `||` - Logical OR
- `()` - Parentheses for grouping

---

## Navigation Commands

During wizard:
- **[number]** - Select option or enter next step
- **[Enter]** - Advance to next step (when field filled)
- **p / prev** - Go back to previous step
- **q / quit** - Cancel wizard

---

## Common Use Cases

### 1. Verify 1080p Video Timing
```bash
> new hact
Hsync: i_hsync
Data Enable: i_de
Min: 1920
Max: 1920
```

### 2. Check Horizontal Sync Width
```bash
> new hsw
Count Trigger: i_clk
Target Pulse: i_hsync
Min: 44
Max: 44
```

### 3. Validate Vertical Back Porch
```bash
> new vbp
Vsync: i_vsync
Data Enable: i_de
Min: 36
Max: 36
```

---

## Tips & Best Practices

1. **Use Signal Aliases**
   - [0] custom expression supports i1, i2, o1, etc.
   - Example: `i1 & i2` instead of full signal names

2. **Validate Before Creating**
   - Check the preview panel on the right
   - Verify all signals are correct
   - Confirm min/max ranges

3. **Min = Max for Exact Values**
   - For strict timing: `Min: 100, Max: 100`
   - For range: `Min: 95, Max: 105`

4. **Use Previous Step**
   - Made a mistake? Type `p` to go back
   - Fix the error and continue

5. **Check Plugin Status**
   - Red text = Plugin or Excel sheet missing
   - Green text = Ready to use
   - Type `new` to see status

---

## Troubleshooting

### "Plugin_missing" or "Excel_missing"
- Plugin file doesn't exist in `scripts/assertions/`
- Excel sheet doesn't exist in your Excel file
- **Solution**: Ensure all plugin files are present

### "Invalid expression: unknown signal 'xyz'"
- Signal name doesn't exist in module
- **Solution**: 
  1. Check available signals in list
  2. Type signal name exactly as shown
  3. Or use numeric aliases (i1, i2, o1, etc.)

### Max < Min Error
- Maximum value must be >= minimum value
- **Solution**: Enter a larger maximum value

### Signal Not Found
- Module not scanned yet
- **Solution**: Run `scan` command first

---

## Complete Workflow

```bash
# 1. Set up environment
> set rtl path/to/rtl
> set module my_video_module
> scan

# 2. Create multiple assertions
> new hact
[...configure...]

> new hsw
[...configure...]

> new vbp
[...configure...]

# 3. Generate assertion files
> gen

# 4. Check output
Files created in: out/assertions/
```

---

## Quick Reference Table

| Type | Purpose | Key Signals | Typical Range |
|------|---------|-------------|---------------|
| HACT | Active pixels per line | hsync, de | 1920, 1280, 640 |
| HSW | Horizontal sync width | trigger, hsync | 44, 96, 128 |
| HBP | Horizontal back porch | hsync, de | 148, 220, 80 |
| HFP | Horizontal front porch | hsync, de | 88, 110, 16 |
| VBP | Vertical back porch | vsync, de | 36, 20, 10 |
| VFP | Vertical front porch | vsync, de | 4, 5, 10 |
| VSW | Vertical sync width | hsync, vsync | 5, 2, 3 |

---

## Next Steps

After creating assertions:
1. **Review Excel File** - Check sheets are populated correctly
2. **Generate Code** - Use `gen` command to create .sv files
3. **Verify Outputs** - Check generated interface/instance files
4. **Integrate** - Add to your testbench

For more details, see:
- `docs/NEW_ASSERTION_TYPES_IMPLEMENTATION.md` - Full implementation details
- `docs/CUSTOM_EXPRESSION_FEATURE.md` - Custom expression guide
- Type `help` in TUI for command reference

---

## Summary

**11 assertion types** now available through interactive TUI wizard:
- ✅ Step-by-step guidance
- ✅ Signal validation  
- ✅ Custom expressions
- ✅ Live preview
- ✅ One command creation

**Start creating assertions now!** 🚀
```
> new hact
```
