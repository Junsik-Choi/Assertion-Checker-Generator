"""
Debug find_module_instances_by_file - Trace upward hierarchy search
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from rtl_parser import (
    find_rtl_root_from, discover_files, build_modules_db,
    find_module_instances_by_file
)

# Setup
p = Path("EDA/RTL/sync_signal.v").resolve()
print(f"Target file: {p}\n")

# Parse modules
rtl_root, _ = find_rtl_root_from(p)
files = sorted(
    set(discover_files(rtl_root, [".v", ".sv"])) |
    set(discover_files(p.parent, [".v", ".sv"])),
    key=lambda f: str(f)
)

modules = build_modules_db(files, allow_unknown=True)
print(f"Total modules parsed: {len(modules)}\n")

# Debug: Check what's in modules
print("=" * 80)
print("MODULES DATABASE CONTENT:")
print("=" * 80)
for mod_name, mod_info in modules.items():
    print(f"\nModule: {mod_name}")
    print(f"  File: {Path(mod_info['file']).name}")
    print(f"  Instances: {len(mod_info.get('instances', []))}")
    if mod_info.get('instances'):
        for inst in mod_info['instances']:
            print(f"    - {inst['inst']} : {inst['type']}")

# Now debug the bottom-up search
print("\n" + "=" * 80)
print("DEBUG: Bottom-up hierarchy search for sync_signal")
print("=" * 80)

target_module = "sync_signal"
print(f"\nSearching for: {target_module}\n")

# Step 1: Find direct usages
print("Step 1: Find who instantiates sync_signal")
print("-" * 80)
direct_usages = []
for mod_name, mod_info in modules.items():
    for child in mod_info.get("instances", []):
        if child["type"] == target_module:
            print(f"  Found: {mod_name} instantiates {child['inst']} (type: {child['type']})")
            direct_usages.append((mod_name, child["inst"]))

print(f"\nTotal direct usages: {len(direct_usages)}")

# Step 2: For each direct usage, trace upward
print("\n" + "=" * 80)
print("Step 2: Trace upward from each usage")
print("=" * 80)

for idx, (parent_module, instance_name) in enumerate(direct_usages, 1):
    print(f"\n[{idx}] Starting from: {parent_module}.{instance_name}")
    print("-" * 80)
    
    current_parent = parent_module
    path = [instance_name]
    depth = 0
    
    while depth < 10:  # Limit iterations for debug
        depth += 1
        print(f"  Iteration {depth}: Looking for who instantiates '{current_parent}'")
        
        found_upper = False
        for mod_name, mod_info in modules.items():
            for child in mod_info.get("instances", []):
                if child["type"] == current_parent:
                    print(f"    -> Found: {mod_name} instantiates {child['inst']} (type: {current_parent})")
                    path.insert(0, child["inst"])
                    current_parent = mod_name
                    found_upper = True
                    break
            if found_upper:
                break
        
        if not found_upper:
            print(f"    -> No parent found for '{current_parent}'. Stopping.")
            break
    
    print(f"  Final path: {'.'.join(path)}")
