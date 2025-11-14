# New Assertion Types Implementation Summary

## Overview

Added support for **7 new video timing assertion types** in the TUI wizard, enabling users to create video signal timing assertions through the interactive `new` command.

## New Assertion Types Added

### 1. HACT (Horizontal Active Pixel Count)
- **Plugin**: `hact`
- **Sheet**: `HACT`
- **Purpose**: Verify active pixel count per horizontal line
- **Fields**:
  - Hsync Signal (horizontal sync)
  - Data Enable Signal  
  - Expected Min Value (minimum pixels)
  - Expected Max Value (maximum pixels)

### 2. HSW (Horizontal Sync Width)
- **Plugin**: `hsw`
- **Sheet**: `HSW`
- **Purpose**: Verify horizontal sync pulse width
- **Fields**:
  - Count Trigger (counting trigger signal)
  - Target Pulse (pulse to monitor)
  - Expected Min Value (minimum width)
  - Expected Max Value (maximum width)

### 3. HBP (Horizontal Back Porch)
- **Plugin**: `hbp`
- **Sheet**: `HBP`
- **Purpose**: Verify timing between hsync and data enable start
- **Fields**:
  - Hsync Signal
  - Data Enable Signal
  - Expected Min Value (minimum cycles)
  - Expected Max Value (maximum cycles)

### 4. HFP (Horizontal Front Porch)
- **Plugin**: `hfp`
- **Sheet**: `HFP`
- **Purpose**: Verify timing between data enable end and hsync
- **Fields**:
  - Hsync Signal
  - Data Enable Signal
  - Expected Min Value (minimum cycles)
  - Expected Max Value (maximum cycles)

### 5. VBP (Vertical Back Porch)
- **Plugin**: `vbp`
- **Sheet**: `VBP`
- **Purpose**: Verify lines between vsync and first active line
- **Fields**:
  - Vsync Signal (vertical sync)
  - Data Enable Signal
  - Expected Min Value (minimum lines)
  - Expected Max Value (maximum lines)

### 6. VFP (Vertical Front Porch)
- **Plugin**: `vfp`
- **Sheet**: `VFP`
- **Purpose**: Verify lines between last active line and vsync
- **Fields**:
  - Vsync Signal
  - Data Enable Signal
  - Expected Min Value (minimum lines)
  - Expected Max Value (maximum lines)

### 7. VSW (Vertical Sync Width)
- **Plugin**: `vsw`
- **Sheet**: `VSW`
- **Purpose**: Verify vertical sync pulse width in lines
- **Fields**:
  - Hsync Signal (for line counting)
  - Vsync Signal
  - Expected Min Value (minimum lines)
  - Expected Max Value (maximum lines)

## Implementation Details

### Code Changes

#### 1. Field Definitions (`_get_plugin_fields`)
Location: `cli_tui.py` line ~4601

Added complete field definitions for all 7 new assertion types with:
- Step-by-step configuration flow
- Signal selection fields
- Min/Max value inputs
- Clear descriptions and examples

#### 2. Plugin Descriptions (`_get_plugin_description`)
Location: `cli_tui.py` line ~4552

Added descriptive text for each plugin:
```python
'hact': 'Horizontal Active Pixel Count - Verify active pixels per line within min/max range',
'hsw': 'Horizontal Sync Width - Verify horizontal sync pulse width',
'hbp': 'Horizontal Back Porch - Verify timing between hsync and data enable start',
'hfp': 'Horizontal Front Porch - Verify timing between data enable end and hsync',
'vbp': 'Vertical Back Porch - Verify lines between vsync and first active line',
'vfp': 'Vertical Front Porch - Verify lines between last active line and vsync',
'vsw': 'Vertical Sync Width - Verify vertical sync pulse width in lines',
```

#### 3. Preview Generation (`_generate_assertion_preview`)
Location: `cli_tui.py` line ~5653

Added preview generation for all 7 types showing:
- Configuration summary
- Signal assignments
- Expected value ranges
- Purpose description

## Usage

### Creating New Assertions

```bash
# Start TUI
> new hact

# Follow step-by-step wizard:
Step 1: Select Hsync Signal
Step 2: Select Data Enable Signal
Step 3: Enter Expected Min Value
Step 4: Enter Expected Max Value
Step 5: Review and Confirm
```

### Available Commands

All new assertion types work with:
- `new hact` - Horizontal Active Pixel Count
- `new hsw` - Horizontal Sync Width
- `new hbp` - Horizontal Back Porch
- `new hfp` - Horizontal Front Porch
- `new vbp` - Vertical Back Porch
- `new vfp` - Vertical Front Porch
- `new vsw` - Vertical Sync Width

### Integration with Existing Features

All new assertion types support:
- ✅ **Custom Expression Input** - [0] option for complex signal expressions
- ✅ **Signal Validation** - Validates signals exist in module
- ✅ **Preview Display** - Shows configuration before creation
- ✅ **Excel Integration** - Writes to corresponding sheets
- ✅ **Auto-advance** - Moves to next step after each input

## Testing

The implementation leverages existing assertion wizard infrastructure, so all new types automatically benefit from:

1. **Signal Selection**
   - Module ports (inputs/outputs)
   - MS signals (user-defined)
   - Custom expressions with validation

2. **Wizard Flow**
   - Step-by-step progression
   - Previous step navigation ('p'/'prev')
   - Confirmation screen
   - Cancel option ('q')

3. **Error Handling**
   - Missing signals detected
   - Invalid inputs rejected
   - Min/Max validation (Max >= Min)

## File Structure

```
scripts/
  cli_tui.py          # Updated with new assertion definitions
  assertions/
    HACT.py           # Existing plugin (backend)
    HSW.py            # Existing plugin (backend)
    HBP.py            # Existing plugin (backend)
    HFP.py            # Existing plugin (backend)
    VBP.py            # Existing plugin (backend)
    VFP.py            # Existing plugin (backend)
    VSW.py            # Existing plugin (backend)
    registry.py       # Plugins already registered
```

## Compatibility

All new assertions are **fully compatible** with:
- Existing TUI wizard system
- Custom expression feature ([0] option)
- Excel generation (gen command)
- Plugin system architecture

## Video Timing Context

These assertions are specifically designed for video signal verification:

### Horizontal Timing
```
←─ HBP ─→←───── HACT ─────→←─ HFP ─→
          ┌─────────────────┐
_____     │  Active Video   │     _____
     |____|                 |____|
     ←─HSW─→                     
```

### Vertical Timing
```
←─ VBP ─→
┌───────────┐
│  Active   │ ← Multiple lines
│  Video    │
│  Region   │
└───────────┘
←─ VFP ─→
←─VSW─→
```

## Benefits

1. **Complete Video Timing Coverage** - All standard video timing parameters can now be verified
2. **Consistent UX** - Same wizard experience across all assertion types
3. **Reusable Infrastructure** - Leverages existing TUI wizard framework
4. **Flexible Input** - Custom expressions supported for all signal fields
5. **Professional UI** - Clear descriptions and preview displays

## Migration Notes

For users familiar with the command-line plugins:
- **Old way**: Manual Excel editing + plugin execution
- **New way**: Interactive TUI wizard with validation

All existing Excel sheets and plugin files remain unchanged - this implementation only adds TUI wizard support for easier creation.

## Statistics

- **Lines added**: ~360 lines
- **Assertion types added**: 7
- **Total fields defined**: 28 (4 fields × 7 types)
- **Preview implementations**: 7 complete preview generators
- **Backward compatibility**: 100% - no breaking changes

## Conclusion

Successfully added complete TUI wizard support for all 7 video timing assertion types. Users can now create these assertions interactively through the `new` command with step-by-step guidance, validation, and preview capabilities.

The implementation follows the existing counter/handshake/pulseWidth patterns, ensuring consistency and maintainability.
