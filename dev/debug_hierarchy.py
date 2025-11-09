#!/usr/bin/env python3
"""
디버그: find_module_instances_by_file가 작동하는지 확인
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from rtl_parser import (
    discover_files,
    find_rtl_root_from,
    build_modules_db,
    find_module_instances_by_file,
)

# Test file: sync_signal.v
rtl_file = Path("EDA/RTL/sync_signal.v").resolve()

print("=" * 80)
print("DETAILED DEBUG: find_module_instances_by_file")
print("=" * 80)
print()

# 1. Build modules database
rtl_root, _ = find_rtl_root_from(rtl_file)
start_scope_dir = rtl_file.parent
files = sorted(
    set(discover_files(rtl_root, [".v", ".sv"]))
    | set(discover_files(start_scope_dir, [".v", ".sv"])),
    key=lambda f: str(f)
)

print(f"RTL file: {rtl_file.name}")
print(f"Files discovered: {len(files)}\n")

# 2. Parse all modules
modules = build_modules_db(files, allow_unknown=True)

print(f"Modules parsed: {len(modules)}\n")

# 3. Find modules in this file
file_modules = set()
for mod_name, mod_info in modules.items():
    if Path(mod_info["file"]).resolve() == rtl_file:
        file_modules.add(mod_name)
        print(f"Module in file: {mod_name}")

if not file_modules:
    print("ERROR: No modules found in file!")
else:
    print(f"\nModules found in file: {file_modules}\n")
    
    # Try to find instances
    print("=" * 80)
    print("Searching for instances...")
    print("=" * 80)
    
    instances = find_module_instances_by_file(modules, rtl_file)
    
    print(f"\nInstances found: {len(instances)}\n")
    
    if instances:
        for i, inst in enumerate(instances, 1):
            print(f"[{i}] {inst['hierarchy_path']}")
    else:
        print("ERROR: No instances found!")
        print("\nDebugging info:")
        print(f"  - All modules in DB: {list(modules.keys())}")
        print(f"  - Modules in this file: {file_modules}")
        print("\nLet's check if these modules are instantiated in any parent module:")
        
        for mod in file_modules:
            print(f"\n  Looking for '{mod}' instantiations...")
            found = False
            for parent_mod, parent_info in modules.items():
                for inst in parent_info.get("instances", []):
                    if inst["type"] == mod:
                        print(f"    ✓ Found in {parent_mod}: {inst['inst']} ({inst['type']})")
                        found = True
            if not found:
                print(f"    ✗ NOT FOUND anywhere!")
