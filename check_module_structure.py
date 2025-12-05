#!/usr/bin/env python3
"""
Check the actual module structure
"""
import sys
sys.path.insert(0, 'scripts')

from rtl_parser import extract_modules_from_text, preprocess

with open('EDA/RTL/blur_scaler.v', 'r', encoding='utf-8') as f:
    content = f.read()

content = preprocess(content)
modules = extract_modules_from_text(content)

if modules:
    module = modules[0]
    print("Module keys:", list(module.keys()))
    print("\nModule structure:")
    for key in module.keys():
        val = module[key]
        if isinstance(val, list):
            print(f"  {key}: list of {len(val)} items")
            if val:
                print(f"    First item: {val[0]}")
        else:
            print(f"  {key}: {type(val).__name__}")
else:
    print("No modules found")
