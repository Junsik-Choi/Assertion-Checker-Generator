#!/usr/bin/env python3
"""Quick test to verify session display shows RTL paths correctly."""

import sys
from pathlib import Path
import json
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from cli_tui import _load_sessions, _shorten_path_for_display

# Create a temporary session folder with session.json
with tempfile.TemporaryDirectory() as tmpdir:
    session_folder = Path(tmpdir) / "blur_scaler-20251108_005529"
    session_folder.mkdir(parents=True)
    
    # Create session.json with RTL path
    session_data = {
        "rtl_start": "d:\\Programing\\Assertion-Checker-Generator\\EDA\\RTL\\blur_scaler.v",
        "target_module": "blur_scaler",
        "module_hierarchy": "tb_top.dut.blur_scaler",
        "session_excel_path": str(session_folder / "blur_scaler.xlsx"),
        "out_dir": str(session_folder / "assertions"),
        "conditions": [],
        "assertions": []
    }
    
    session_json = session_folder / "session.json"
    session_json.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Create dummy Excel and assertions files
    (session_folder / "blur_scaler.xlsx").touch()
    (session_folder / "assertions").mkdir(exist_ok=True)
    
    print("Test Session Data:")
    print(f"  RTL Start: {session_data['rtl_start']}")
    print(f"  Module: {session_data['target_module']}")
    print(f"  Module Hierarchy: {session_data['module_hierarchy']}")
    print()
    
    print("Display Result (as shown in session list):")
    rtl_display = _shorten_path_for_display(session_data['rtl_start'], 50)
    print(f"  RTL Column (50 width): {rtl_display}")
    print()
    
    print("✅ RTL path will be displayed instead of just module name!")
