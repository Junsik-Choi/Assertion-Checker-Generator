# File Generation Preview Enhancement - Implementation Summary

## Overview
Enhanced the file generation wizard's preview step to show **complete file content** with **pagination support** using n/N navigation keys.

## Date
November 10, 2025

## Problem
The previous implementation only showed the first 5 lines of generated files:
```
Preview (first 5 lines):
  // Auto-generated interface file
  // Generated: 2025-11-10 ...
  //
  // ===== ASSERTIONS =====
  // [1] COUNTER assertion
```

Users couldn't see the full file content before generating, making it difficult to verify the output.

## Solution
Implemented full-page preview with scrolling and pagination:
- Show **complete file content** with line numbers
- Support **n/N navigation** to scroll through content
- Add **'f' key** to switch between interface/instance files in "both" mode
- Display pagination info (e.g., "Page 2/5 - Use n/N to navigate")

## Changes Made

### 1. Added Pagination State Variables

**File**: `scripts/cli_tui.py` (lines ~420-421)

```python
gen_preview_page: int = 0  # Current page in preview (for pagination)
gen_preview_file_idx: int = 0  # 0=interface, 1=instance (for "both" mode)
```

### 2. Created Preview Content Generator

**Function**: `_generate_preview_content()` (lines ~5619-5646)

```python
def _generate_preview_content(state: AppState) -> List[str]:
    """Generate full preview content for file generation wizard."""
    # Determine what to include
    include_asserts = state.gen_data_source in ('1', '3')
    include_signals = state.gen_data_source in ('2', '3')
    
    # For "both" mode, show file selected by gen_preview_file_idx
    if state.gen_file_type == 3:  # Both
        if state.gen_preview_file_idx == 0:
            content = _generate_interface_content(state, include_asserts, include_signals)
        else:
            content = _generate_instance_content(state, include_asserts, include_signals)
    elif state.gen_file_type == 1:  # Interface
        content = _generate_interface_content(state, include_asserts, include_signals)
    else:  # Instance
        content = _generate_instance_content(state, include_asserts, include_signals)
    
    return content.split('\n')
```

This function:
- Generates complete file content (not just first 5 lines)
- Handles "both" mode by selecting appropriate file
- Returns list of lines for pagination

### 3. Enhanced Preview Rendering

**Function**: `_render_gen_wizard()` preview stage (lines ~4780-4835)

**Before**:
```python
preview_lines = state.gen_preview_lines[:5]  # Only first 5 lines
for i, line in enumerate(preview_lines):
    stdscr.addnstr(y_start + 7 + i, margin_x + 2, line, ...)
```

**After**:
```python
# Calculate pagination
available_lines = max_y - preview_start_y - 4
lines_per_page = max(10, available_lines)
total_pages = max(1, (total_lines + lines_per_page - 1) // lines_per_page)

# Get lines for current page
start_line = state.gen_preview_page * lines_per_page
end_line = min(start_line + lines_per_page, total_lines)

# Show with line numbers
for i, line in enumerate(preview_lines):
    line_num = f"{start_line + i + 1:4d} "
    stdscr.addnstr(line_y, margin_x, line_num, ...)
    stdscr.addnstr(line_y, margin_x + len(line_num), line, ...)
```

Features:
- Dynamic lines-per-page based on terminal height
- Line numbers for easy reference
- Page info header showing current range
- Pagination indicator at bottom

### 4. Added Navigation Commands

**File**: Input handling in main loop (lines ~1190-1210)

```python
elif state.gen_wizard_stage == 'preview':
    if cmdline == '':  # Empty = generate
        msg = _generate_files(state)
        state.gen_wizard_active = False
    elif cmdline == 'n':  # Next page
        state.gen_preview_page += 1
    elif cmdline == 'N':  # Previous page
        state.gen_preview_page = max(0, state.gen_preview_page - 1)
    elif cmdline == 'f':  # Switch file (for "both" mode)
        if state.gen_file_type == 3:
            state.gen_preview_file_idx = 1 - state.gen_preview_file_idx
            state.gen_preview_page = 0
            state.gen_preview_lines = _generate_preview_content(state)
        else:
            status_msg = "Only one file type selected"
    elif cmdline == 'b':
        state.gen_wizard_stage = 'data_source'
    else:
        status_msg = "ERROR: ..."
```

Commands:
- **n**: Scroll to next page
- **N**: Scroll to previous page
- **f**: Switch between interface/instance (both mode only)
- **Enter**: Generate files
- **b**: Go back to edit configuration
- **q**: Cancel wizard

### 5. Updated Hint Messages

**File**: Main loop hint line (lines ~1119-1123)

```python
elif state.gen_wizard_stage == 'preview':
    if state.gen_file_type == 3:
        hint_line = "[Enter] to generate | n/N scroll | 'f' switch file | 'b' edit | 'q' cancel"
    else:
        hint_line = "[Enter] to generate | n/N scroll | 'b' edit | 'q' cancel"
```

Dynamic hints based on file type selection.

### 6. Initialize Preview on Entry

**File**: Data source stage handling (lines ~1178-1184)

```python
if cmdline in ('1', '2', '3'):
    state.gen_data_source = cmdline
    state.gen_wizard_stage = 'preview'
    state.gen_preview_page = 0
    state.gen_preview_file_idx = 0
    # Generate full preview content
    state.gen_preview_lines = _generate_preview_content(state)
```

Preview content is generated immediately when entering preview stage.

## Visual Comparison

### Before (Old Preview)
```
Step 4/4: Generate Files

Filename: my_output
File Type: Both
Data Source: Both

Preview (first 5 lines):
  // Auto-generated interface file
  // Generated: 2025-11-10 ...
  //
  // ===== ASSERTIONS =====
  // [1] COUNTER assertion

[Enter] to generate | 'b' to edit | 'q' to cancel
```

### After (New Preview)
```
Step 4/4: Generate Files - Preview

Filename: my_output
File Type: Both
Data Source: Both
Viewing: Interface (.if.sv) (press 'f' to switch)

Preview (lines 1-25 of 87):
   1 // Auto-generated interface file
   2 // Generated: 2025-11-10 14:30:45
   3 //
   4 // ===== ASSERTIONS =====
   5 // [1] COUNTER assertion
   6 //     Name: cnt_check
   7 //     Target: cnt
   8 //     Increment: i_data
   9 //     Reset: i_reset
  10 //     Trigger: o_valid
  11 //     Expected: 10
  12 //
  13 // [2] PULSEWIDTH assertion
  14 //     Name: pulse_check
  15 //     Type: hpulse
  16 //     Base Clock: i_clk
  17 //     Target: o_valid
  18 //     Min Width: 1
  19 //     Max Width: 5
  20 //
  21 // ===== SIGNALS =====
  22 // Input signals:
  23 //   - i_clk (1 bits)
  24 //   - i_reset (1 bits)
  25 //   - i_data (8 bits)

Page 1/4 - Use n/N to navigate

[Enter] to generate | n/N scroll | 'f' switch file | 'b' edit | 'q' cancel
```

## Key Features

### 1. Complete Content Display
- Shows **entire file**, not just first 5 lines
- All assertions listed with full details
- All signals displayed with widths
- Proper SystemVerilog comments format

### 2. Pagination
- Dynamic page size based on terminal height
- Smooth scrolling with n/N keys
- Page counter shows current position
- Line numbers for easy reference

### 3. File Switching (Both Mode)
- Press 'f' to toggle between interface and instance
- Resets page to 0 when switching
- Clear indicator shows current file
- Only available when "both" selected

### 4. Navigation Controls
```
n    - Next page (scroll down)
N    - Previous page (scroll up)
f    - Switch file (both mode only)
b    - Back to configuration
q    - Cancel wizard
Enter - Generate files
```

### 5. Smart Pagination
- Automatically clamps page number to valid range
- Calculates total pages based on content length
- Shows line range in header (e.g., "lines 26-50 of 87")
- Last page shows exactly to end of file

## Usage Example

### Step-by-Step Flow

1. **Start File Generation** (Main page → 'f'):
   ```
   Step 1/4: Filename
   Enter filename (without extension): my_output
   ```

2. **Select File Type**:
   ```
   Step 2/4: File Type
   1. Interface (.if.sv)
   2. Instance (.inst.sv)
   3. Both
   Enter: 3
   ```

3. **Select Data Source**:
   ```
   Step 3/4: Data Source
   1. Assertions only
   2. Signals only
   3. Both
   Enter: 3
   ```

4. **Preview and Navigate**:
   ```
   Step 4/4: Generate Files - Preview
   
   Viewing: Interface (.if.sv) (press 'f' to switch)
   
   Preview (lines 1-25 of 87):
      1 // Auto-generated interface file
      2 // Generated: 2025-11-10 ...
      ... (content) ...
     25 //   - i_data (8 bits)
   
   Page 1/4 - Use n/N to navigate
   
   > n            ← Press 'n' to see next page
   ```

5. **View Next Page**:
   ```
   Preview (lines 26-50 of 87):
     26 //   - i_en (1 bits)
     27 //
     28 // Output signals:
     ... (more content) ...
   
   Page 2/4 - Use n/N to navigate
   
   > N            ← Press 'N' to go back
   ```

6. **Switch to Instance File**:
   ```
   > f
   
   Viewing: Instance (.inst.sv) (press 'f' to switch)
   
   Preview (lines 1-25 of 89):
      1 // Auto-generated instance file
      ... (instance content) ...
   ```

7. **Generate Files**:
   ```
   > [Enter]
   
   Generated 2 file(s):
     my_output.if.sv
     my_output.inst.sv
   ```

## Benefits

### For Users
1. **Full Visibility**: See complete file content before generating
2. **Verification**: Check all assertions and signals are included
3. **Navigation**: Easy scrolling through long files
4. **Confidence**: Know exactly what will be generated

### Technical Benefits
1. **Reusable Code**: Leverages existing content generators
2. **Dynamic Layout**: Adapts to terminal size
3. **Efficient**: Only renders visible lines
4. **Maintainable**: Clean separation of concerns

## Testing

### Test Results
```
✅ TEST 1 PASSED: Preview Content Generation
✅ TEST 2 PASSED: Pagination State Management
✅ TEST 3 PASSED: Both Mode File Switching
✅ TEST 4 PASSED: Preview Display Logic

🎉 ALL 4 TESTS PASSED
```

### Test Coverage
- Preview content generation for both file types
- Pagination state initialization and navigation
- File switching in "both" mode
- Page boundary calculations
- Line number formatting
- Dynamic page size calculation

## Files Modified

1. **scripts/cli_tui.py** (6761 lines):
   - Added pagination state variables (lines ~420-421)
   - Created `_generate_preview_content()` function (lines ~5619-5646)
   - Enhanced preview rendering (lines ~4780-4835)
   - Added navigation commands (lines ~1190-1210)
   - Updated hint messages (lines ~1119-1123)
   - Initialize preview on entry (lines ~1178-1184)

2. **dev/test_file_preview.py** (220 lines):
   - Comprehensive test suite
   - 4 test sections covering all features
   - All tests passing

3. **docs/FILE_PREVIEW_ENHANCEMENT.md**:
   - Complete documentation (this file)

## Known Limitations

1. **Very Long Files**: Files with 1000+ lines may be slow to generate
   - Currently generates full content immediately
   - Could optimize with lazy generation if needed

2. **Wide Lines**: Lines longer than terminal width are truncated
   - Uses `_truncate()` helper
   - No horizontal scrolling implemented

3. **Syntax Highlighting**: Preview shows plain text
   - No SystemVerilog syntax highlighting
   - Could be added in future enhancement

## Future Enhancements

1. **Search in Preview**: Add '/' to search within preview
2. **Jump to Line**: Add 'g' command to jump to specific line
3. **Syntax Highlighting**: Color-code SystemVerilog syntax
4. **Export Preview**: Save preview to temporary file for external viewing
5. **Diff View**: Show diff between interface and instance side-by-side

## Related Features

- Signal list pagination (same n/N pattern)
- Assertion wizard preview (right panel preview)
- Session display pagination

## Conclusion

Successfully implemented comprehensive preview enhancement with:
- ✅ Complete file content display (not just 5 lines)
- ✅ Pagination with n/N navigation
- ✅ Line numbers for easy reference
- ✅ File switching in "both" mode
- ✅ Dynamic layout adaptation
- ✅ All automated tests passing

The feature is ready for use and provides users with full visibility into generated files before committing to file creation.
