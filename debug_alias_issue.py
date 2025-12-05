#!/usr/bin/env python3
"""
Debug MS command alias resolution issue
"""
import sys
import re

# Simulate the problem step by step

print("="*70)
print("PROBLEM ANALYSIS: ms last_de_out ( i9 != 7 ) && o2")
print("="*70)

# Input data - from blur_scaler.v
inputs = [
    "i_blur_mode_cap",      # i1
    "i_den",                # i2
    "i_hor_cnt [10:0]",     # i3
    "i_hsync",              # i4
    "i_mirror_mode_cap",    # i5
    "i_sram_rd1 [7:0]",     # i6
    "i_sram_rd2 [7:0]",     # i7
    "i_sram_rd3 [7:0]",     # i8
    "i_vact_state [10:0]",  # i9
    "i_vsync",              # i10
    "i_w1_cap [3:0]",       # i11
    "i_w2_cap [3:0]",       # i12
    "i_w3_cap [3:0]",       # i13
    "i_w4_cap [3:0]",       # i14
    "i_w5_cap [3:0]",       # i15
    "i_w6_cap [3:0]",       # i16
    "i_w7_cap [3:0]",       # i17
    "i_w8_cap [3:0]",       # i18
    "i_w9_cap [3:0]",       # i19
    "i_weight_wr_mode_cap", # i20
]

outputs = [
    "o_data [7:0]",         # o1
    "o_den",                # o2
    "o_hsync",              # o3
    "o_vsync",              # o4
]

print(f"\nTotal Inputs: {len(inputs)}")
for i, inp in enumerate(inputs, 1):
    print(f"  i{i} → {inp}")

print(f"\nTotal Outputs: {len(outputs)}")
for i, out in enumerate(outputs, 1):
    print(f"  o{i} → {out}")

print("\n" + "="*70)
print("STEP 1: Original Expression")
print("="*70)
expr = "( i9 != 7 ) && o2"
print(f"expr = '{expr}'")

print("\n" + "="*70)
print("STEP 2: Tokenization")
print("="*70)

def tokenize_expr(expr: str):
    """Tokenize expression using regex"""
    token_pattern = r'''
        <<<|>>>|===|!==|<<|>>|<=|>=|==|!=|&&|\|\||\*\*
        |[&|^~!+\-*/%<>()[\]{}?:=,;]
        |[A-Za-z_]\w*
        |\d+
    '''
    tokens = re.findall(token_pattern, expr, re.VERBOSE)
    return tokens

tokens = tokenize_expr(expr)
print(f"tokens = {tokens}")

print("\n" + "="*70)
print("STEP 3: Alias Resolution (What SHOULD happen)")
print("="*70)

resolved = []
for token in tokens:
    m = re.match(r'^i(\d+)$', token)
    if m:
        idx = int(m.group(1))
        if 1 <= idx <= len(inputs):
            resolved_name = inputs[idx-1].split()[0]  # Get first token (name without width)
            print(f"  {token} → i{idx} → {resolved_name}")
            resolved.append(resolved_name)
        else:
            print(f"  {token} → ERROR: i{idx} out of range (only have {len(inputs)} inputs)")
            resolved.append(token)  # Keep original if out of range
        continue
    
    m = re.match(r'^o(\d+)$', token)
    if m:
        idx = int(m.group(1))
        if 1 <= idx <= len(outputs):
            resolved_name = outputs[idx-1].split()[0]  # Get first token (name without width)
            print(f"  {token} → o{idx} → {resolved_name}")
            resolved.append(resolved_name)
        else:
            print(f"  {token} → ERROR: o{idx} out of range (only have {len(outputs)} outputs)")
            resolved.append(token)  # Keep original if out of range
        continue
    
    print(f"  {token} → {token} (not an alias)")
    resolved.append(token)

print(f"\nresolved_tokens = {resolved}")

print("\n" + "="*70)
print("STEP 4: Current Implementation Issue")
print("="*70)

print("""
In cli_tui.py lines 2933-2937:

    expr_tokens = _tokenize_expr(expr)              # Original: ( i9 != 7 ) && o2
    expr_tokens = [ _alias_replace(t) for t in expr_tokens ]
    expr = _join_expr_tokens(expr_tokens)           # Should be: ( i_vact_state != 7 ) && o_den
    
    # ... then validation ...
    ok, err = _validate_condition_expr(expr, state) # Uses updated 'expr'

However, the problem might be:
1. The alias replacement logic might be failing silently
2. The _join_expr_tokens might not be working correctly
3. The validation might be receiving the ORIGINAL expr without aliases
""")

print("\n" + "="*70)
print("STEP 5: Check current cli_tui.py implementation")
print("="*70)

# Read the actual code
with open('scripts/cli_tui.py', 'r') as f:
    lines = f.readlines()

print("\nLines 2933-2940 (ms command processing):")
for i in range(2932, 2940):
    if i < len(lines):
        print(f"  {i+1:4d}: {lines[i]}", end='')

print("\n\nLooking for the _validate_condition_expr call...")
for i in range(2933, 2950):
    if i < len(lines) and '_validate_condition_expr' in lines[i]:
        print(f"  {i+1:4d}: {lines[i]}", end='')
        print(f"  {i+2:4d}: {lines[i+1]}", end='')
        break

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("""
The issue is likely that:

1. ✓ Tokenization works correctly: ['(', 'i9', '!=', '7', ')', '&&', 'o2']
2. ? Alias resolution happens: ['(', 'i_vact_state', '!=', '7', ')', '&&', 'o_den']
3. ? Join happens correctly
4. ? The updated 'expr' is passed to validation

LIKELY PROBLEM: The validation function might be receiving the ORIGINAL
expression instead of the alias-resolved one!

Check if _validate_condition_expr is called with the correct expr variable.
""")
