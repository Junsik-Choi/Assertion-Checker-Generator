# Gen Command Enhancement - Updated Plugin Compatibility

## Date
November 12, 2025

## Overview
Enhanced the TUI `gen` command to be fully compatible with updated assertion plugins, particularly `delayCondition.py` and `pulseWidth.py` which now support multiple assertion generation and improved structure.

## Analysis of Plugin Changes

### 1. DelayCondition Plugin (`scripts/assertions/delayCondition.py`)

#### Key Changes:
- **Multiple Sets Support**: Now generates multiple delay condition assertions in a single module
- **Label-Below Pattern**: Uses column-based layout (Trigger, Delay1, Delay2, Result)
- **Unified Module**: Generates `assertion_delayCondition` with multiple properties
- **Incremental Addition**: Supports adding multiple assertions in one session

#### Output Format:
```python
def generate_sv(parsed, context) -> List[str]:
    return [sv_module_code, inst_code]
```

**Module Structure**:
```systemverilog
module assertion_delayCondition
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [0:0] i_trigger1,
    input logic [0:0] i_result1,
    input logic [0:0] i_trigger2,
    input logic [0:0] i_result2
);

property p_delayCondition_check1(trigger, result);
    @(posedge i_clk) disable iff(!i_rstn)
    $rose(trigger) |-> ##[1 : 5] $rose(result);
endproperty

assert property (p_delayCondition_check1(i_trigger1, i_result1)) 
    else $error("failed at %t", $time);

property p_delayCondition_check2(trigger, result);
    @(posedge i_clk) disable iff(!i_rstn)
    $rose(trigger) |-> ##[2 : 10] $rose(result);
endproperty

assert property (p_delayCondition_check2(i_trigger2, i_result2)) 
    else $error("failed at %t", $time);

endmodule
```

### 2. PulseWidth Plugin (`scripts/assertions/pulseWidth.py`)

#### Key Changes:
- **Fixed Table Structure**: 5 columns (Type, Count_Trigger, Target_Pulse, Expected_Min_Value, Expected_Max_Value)
- **Two Module Types**: 
  - `assertion_hpulse` for horizontal pulse width checking
  - `assertion_vpulse` for vertical pulse width checking
- **Type Selection**: User selects hpulse or vpulse before input

#### Output Format:
```python
def generate_sv(parsed, context) -> List[str]:
    return [combined_sv_modules, combined_inst_code]
```

**hpulse Module**:
```systemverilog
module assertion_hpulse
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [7:0] i_signal,
    input logic [3:0] i_min,
    input logic [3:0] i_max
);

property p_hpulse;
    int value_count;
    @(posedge i_clk) disable iff(!i_rstn)
    (i_signal) |-> (1, value_count = 0)
    ##1 (i_signal, value_count = value_count + 1)[*0:$]
    ##1 (!i_signal, value_count = value_count + 1)
    ##0 (i_min <= value_count && value_count <= i_max);
endproperty

assert property (p_hpulse) else $error("failed at %t", $time);

endmodule
```

**vpulse Module**:
```systemverilog
module assertion_vpulse
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [0:0] i_count_trig,
    input logic [7:0] i_signal,
    input logic [3:0] i_min,
    input logic [3:0] i_max
);

sequence s_vpulse(value_count);
    @(negedge i_count_trig)
    (i_signal, value_count = value_count + 1)[*0:$]
    ##1 (!i_signal);
endsequence

property p_vpulse;
    int value_count;
    @(posedge i_count_trig) disable iff(!i_rstn)
    (i_signal) |-> (1, value_count = 0)
    ##0 s_vpulse(value_count)
    ##1 (i_min <= value_count && value_count <= i_max);
endproperty

assert property (p_vpulse) else $error("failed at %t", $time);

endmodule
```

### 3. Counter & Handshake Plugins (Unchanged)

Both plugins continue to work with existing format:
- **Counter**: `assertion_counter` module
- **Handshake**: `assertion_gen` module (supports 2phase/4phase/ready_valid)

## TUI Gen Command Enhancements

### Changes Made to `scripts/cli_tui.py`

#### 1. Enhanced Plugin Data Detection (lines ~5743-5780)

**Problem**: Original code only checked for `parsed.get("blocks")`, which didn't match delayCondition's format.

**Solution**:
```python
# Handle both old format (dict with "blocks") and new format (direct dict)
blocks = parsed.get("blocks") if isinstance(parsed, dict) else None

# For delayCondition: check "sets" instead of "blocks"
if not blocks and isinstance(parsed, dict):
    if parsed.get("sets"):
        blocks = parsed.get("sets")
    elif any(key in parsed for key in ("Base Clock", "Base Reset", "unique_ports")):
        # delayCondition format: has Base Clock/Reset but no "blocks" key
        blocks = [parsed]  # Wrap in list for consistency

# Skip if truly no data
if not blocks:
    continue
```

**Benefits**:
- ✅ Works with counter/handshake (`blocks` key)
- ✅ Works with delayCondition (`sets` key)
- ✅ Works with pulseWidth (`blocks` key)
- ✅ Flexible for future plugin formats

#### 2. Improved Error Handling (lines ~5780-5795)

**Before**:
```python
except Exception as e:
    # Skip plugins that fail
    pass
```

**After**:
```python
except KeyError:
    # Sheet doesn't exist - skip this plugin silently
    continue
except Exception as e:
    # Log other errors but continue with remaining plugins
    import sys
    print(f"[Warning] Plugin {pcls.plugin_name} failed: {e}", file=sys.stderr)
```

**Benefits**:
- ✅ Silently skips missing sheets (expected behavior)
- ✅ Logs unexpected errors for debugging
- ✅ Continues with remaining plugins instead of failing completely

#### 3. Enhanced Module Instance Extraction (lines ~5946-5950)

**Before**:
```python
re_module_inst = re.compile(r'^\s*(\w+)\s+(u_\w+)\s*\(\s*\)\s*;', re.MULTILINE)
```

**After**:
```python
# Match both with and without 'u_' prefix: "module_name u_instance_name();" or "module_name instance_name();"
re_module_inst = re.compile(r'^\s*([A-Za-z_]\w+)\s+([A-Za-z_]\w+)\s*\(\s*\)\s*;', re.MULTILINE)
```

**Benefits**:
- ✅ More flexible instance name pattern
- ✅ Handles different naming conventions
- ✅ Works with all plugin output formats

## Testing

### Test Suite: `dev/test_gen_updated_plugins.py`

Created comprehensive tests covering:

1. **DelayCondition Plugin Test**:
   - Multiple assertion sets in one module
   - Multiple properties (p_delayCondition_check1, p_delayCondition_check2)
   - Proper port aggregation
   - ✅ PASSED

2. **PulseWidth Plugin Test**:
   - hpulse module generation
   - vpulse module generation
   - Combined hpulse + vpulse
   - Different module names extracted correctly
   - ✅ PASSED

3. **Mixed Plugins Test**:
   - Counter + Handshake + DelayCondition + PulseWidth together
   - All 4 modules extracted: `assertion_counter`, `assertion_gen`, `assertion_delayCondition`, `assertion_hpulse`
   - ✅ PASSED

**All tests passed: 3/3** ✅

## Compatibility Matrix

| Plugin | Module Name(s) | Return Format | Data Key | Gen Compatible |
|--------|----------------|---------------|----------|----------------|
| **counter** | `assertion_counter` | `[sv, inst]` | `blocks` | ✅ Yes |
| **handshake** | `assertion_gen` | `[sv, inst]` | `blocks` | ✅ Yes |
| **delayCondition** | `assertion_delayCondition` | `[sv, inst]` | `sets` | ✅ Yes (enhanced) |
| **pulseWidth** | `assertion_hpulse`<br>`assertion_vpulse` | `[sv, inst]` | `blocks` | ✅ Yes (enhanced) |

## Usage Example

### In TUI

1. **Start TUI**: `python scripts/cli_tui.py`
2. **Load/Create Session**: Complete onboarding or load existing
3. **Create Assertions**:
   ```
   > new            # Create counter assertion
   > new            # Create handshake assertion  
   > new            # Create delayCondition (multiple sets)
   > new            # Create pulseWidth (hpulse/vpulse)
   ```
4. **Generate Files**:
   ```
   > gen
   Enter filename: my_assertions
   Select file type: [3] Both (interface + instance)
   Select data source: [1] Assertions only
   ```
5. **Preview & Confirm**: Navigate with `n`/`N`, press `y` to generate

### Generated Output

**Interface file** (`my_assertions.if.sv`):
```systemverilog
`include "uvm_macros.svh"
import uvm_pkg::*;

interface assertion_intf
(
    input logic [0:0] i_clk,
    input logic [0:0] i_rstn,
    input logic [7:0] i_data,
    input logic [0:0] i_valid,
    input logic [0:0] req,
    input logic [0:0] ack,
    input logic [0:0] i_trigger1,
    input logic [0:0] i_result1,
    input logic [7:0] i_signal,
    input logic [3:0] i_min,
    input logic [3:0] i_max
);

// counter
reg [31:0] cnt;
always @(posedge i_clk or negedge i_rstn) begin
    if(!i_rstn) cnt <= 0;
    else if(i_valid) cnt <= cnt+1;
end
assert property (p_counter_check) else $error("failed");

// ===== Next plugin section =====

// handshake
property p_2phase_check_0(req, ack);
    @(posedge i_clk) disable iff(!i_rstn)
    (~req & ~ack) |-> ##1 ((req & ~ack) or (req & ack) or (~req & ~ack));
endproperty
assert property (p_2phase_check_0(req, ack)) else $error("failed");

// ===== Next plugin section =====

// delayCondition
property p_delayCondition_check1(trigger, result);
    @(posedge i_clk) disable iff(!i_rstn)
    $rose(trigger) |-> ##[1 : 5] $rose(result);
endproperty
assert property (p_delayCondition_check1(i_trigger1, i_result1)) 
    else $error("failed");

// ===== Next plugin section =====

// pulseWidth
property p_hpulse;
    int value_count;
    @(posedge i_clk) disable iff(!i_rstn)
    (i_signal) |-> (1, value_count = 0)
    ##1 (i_signal, value_count = value_count + 1)[*0:$]
    ##1 (!i_signal, value_count = value_count + 1)
    ##0 (i_min <= value_count && value_count <= i_max);
endproperty
assert property (p_hpulse) else $error("failed");

endinterface
```

**Instance file** (`my_assertions.inst.sv`):
```systemverilog
`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_counter
      u_assertion_counter();

assertion_delayCondition
      u_assertion_delayCondition();

assertion_gen
      u_assertion_gen();

assertion_hpulse
      u_assertion_hpulse();

assign u_assertion_counter.i_clk = top.dut.i_clk;
assign u_assertion_counter.i_rstn = top.dut.i_rstn;
assign u_assertion_counter.i_data = top.dut.i_data;
assign u_assertion_delayCondition.i_clk = top.dut.i_clk;
assign u_assertion_delayCondition.i_rstn = top.dut.i_rstn;
assign u_assertion_delayCondition.i_trigger1 = top.dut.i_trigger1;
assign u_assertion_delayCondition.i_result1 = top.dut.i_result1;
assign u_assertion_gen.ack = top.dut.ack;
assign u_assertion_gen.i_clk = top.dut.i_clk;
assign u_assertion_gen.i_rstn = top.dut.i_rstn;
assign u_assertion_gen.req = top.dut.req;
assign u_assertion_hpulse.i_clk = top.dut.i_clk;
assign u_assertion_hpulse.i_max = top.dut.i_max;
assign u_assertion_hpulse.i_min = top.dut.i_min;
assign u_assertion_hpulse.i_rstn = top.dut.i_rstn;
assign u_assertion_hpulse.i_signal = top.dut.i_signal;
```

## Benefits

### Before Enhancement:
- ❌ Only worked with plugins using `blocks` key
- ❌ Failed silently on delayCondition plugin
- ❌ Couldn't handle multiple assertion sets
- ❌ Hidden errors made debugging difficult

### After Enhancement:
- ✅ Works with all 4 plugins (counter, handshake, delayCondition, pulseWidth)
- ✅ Handles multiple formats (`blocks`, `sets`, direct dict)
- ✅ Supports multiple assertions in one module
- ✅ Better error reporting for debugging
- ✅ Flexible instance name pattern matching
- ✅ Fully tested with comprehensive test suite

## Migration Notes

### For Users:
- **No changes required** - gen command works the same way
- All existing workflows continue to work
- New plugins automatically supported

### For Plugin Developers:
The gen command now supports multiple data formats:

**Option 1: Traditional "blocks" format** (counter, handshake, pulseWidth):
```python
def parse(self, xls_path):
    return {"blocks": [...]}
```

**Option 2: "sets" format** (delayCondition):
```python
def parse(self, xls_path):
    return {"sets": [...], "Base Clock": "...", "unique_ports": [...]}
```

**Option 3: Direct dict format**:
```python
def parse(self, xls_path):
    return {"Base Clock": "...", "Base Reset": "...", "unique_ports": [...]}
```

All formats are automatically detected and handled!

## Known Limitations

1. **No Parallel Execution**: Plugins are processed sequentially
   - Future: Could parallelize for performance

2. **Error Recovery**: If one plugin fails, others continue but failed plugin is skipped
   - Future: Add retry mechanism or partial recovery

3. **Port Conflict Resolution**: If multiple plugins use same port with different widths, last one wins
   - Future: Add conflict detection and user prompt

## Future Enhancements

1. **Plugin Selection**: Allow user to choose which plugins to include
2. **Preview Enhancement**: Show plugin contribution breakdown
3. **Port Width Validation**: Check for conflicts across plugins
4. **Performance Optimization**: Parallel plugin processing
5. **Better Error Messages**: More specific feedback on failures

## Conclusion

Successfully enhanced the TUI `gen` command to support all updated assertion plugins. The changes are backward compatible, thoroughly tested, and provide better error handling and flexibility for future plugins.

✅ **Gen command now fully compatible with all assertion plugins!**
