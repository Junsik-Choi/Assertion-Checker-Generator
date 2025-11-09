#!/usr/bin/env python3
"""Quick test to verify assertion plugins are loaded correctly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _get_assertion_plugins_info

plugins = _get_assertion_plugins_info()
print(f"Total plugins: {len(plugins)}\n")

for i, p in enumerate(plugins, 1):
    fields = p.get("fields", [])
    print(f"{i}. {p['name']}")
    print(f"   Fields: {len(fields)}")
    if fields:
        for j, field in enumerate(fields, 1):
            print(f"     {j}. {field.get('name', '?')}: {field.get('type', '?')}")
    print()
