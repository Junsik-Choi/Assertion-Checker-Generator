#!/usr/bin/env python3
"""
Test to reproduce the original error and verify the fix.
The error was: IndexError: list index out of range
at line 4648: current_field = fields[0]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _get_assertion_plugins_info

# Check if any plugin has empty fields
plugins = _get_assertion_plugins_info()

print("Checking for plugins with empty fields list...\n")

has_empty_fields = False
for i, plugin in enumerate(plugins, 1):
    fields = plugin.get('fields', [])
    print(f"{i}. {plugin['name']}: {len(fields)} fields", end="")
    if not fields:
        print(" ❌ EMPTY - This would cause IndexError!")
        has_empty_fields = True
    else:
        print(" ✅ OK")

print()
if has_empty_fields:
    print("ERROR: Found plugins with empty fields!")
    sys.exit(1)
else:
    print("✅ All plugins have fields defined. Error should not occur.")
    sys.exit(0)
