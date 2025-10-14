"""
TUI 실행 후 결과 확인 스크립트
"""
from pathlib import Path
from datetime import datetime
import json

print("=" * 80)
print("TUI TEST RESULT ANALYSIS")
print("=" * 80)
print(f"\nCurrent time: {datetime.now().strftime('%H:%M:%S')}")

# 1. Debug log 확인
print("\n[1] DEBUG LOG CHECK")
print("-" * 80)
debug_log = Path("out/session_creation_debug.log")
if debug_log.exists():
    print(f"✓ Debug log exists ({debug_log.stat().st_size} bytes)")
    print("\nContent:")
    print(debug_log.read_text(encoding="utf-8"))
else:
    print("❌ Debug log NOT FOUND!")
    print("   → This means _create_session_excel_and_fill() was NEVER called!")

# 2. Sessions 확인
print("\n[2] SESSIONS DIRECTORY CHECK")
print("-" * 80)
sessions_dir = Path("out/sessions")
if sessions_dir.exists():
    items = list(sessions_dir.iterdir())
    folders = [i for i in items if i.is_dir()]
    files = [i for i in items if i.is_file()]
    
    print(f"Total items: {len(items)}")
    print(f"  Folders: {len(folders)}")
    print(f"  Files: {len(files)}")
    
    if folders:
        print("\n📁 SESSION FOLDERS:")
        for folder in sorted(folders, key=lambda x: x.stat().st_mtime, reverse=True):
            print(f"  - {folder.name}/")
            for sub in sorted(folder.iterdir()):
                size = sub.stat().st_size if sub.is_file() else 0
                print(f"      {sub.name} ({size:,} bytes)")
    else:
        print("\n❌ NO SESSION FOLDERS FOUND!")
    
    if files:
        print("\n📄 SESSION SNAPSHOTS (JSON):")
        for file in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
            print(f"  - {file.name} ({file.stat().st_size} bytes)")
            # Read and display
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                print(f"      rtl_start: {data.get('rtl_start', 'N/A')}")
                print(f"      target_module: {data.get('target_module', 'N/A')}")
                print(f"      excel_path: {data.get('excel_path', 'N/A')}")
                session_excel = data.get('session_excel_path', '')
                if session_excel:
                    print(f"      session_excel_path: {session_excel} ✓")
                else:
                    print(f"      session_excel_path: EMPTY ❌")
            except Exception as e:
                print(f"      Error reading: {e}")
else:
    print("❌ Sessions directory not found!")

# 3. Analysis
print("\n[3] ANALYSIS")
print("-" * 80)
if not debug_log.exists():
    print("❌ PROBLEM: _create_session_excel_and_fill() was NOT called")
    print("   Possible reasons:")
    print("   1. Onboarding didn't reach Excel stage")
    print("   2. Different code path was taken")
    print("   3. Exception occurred before logging")
elif not folders:
    print("❌ PROBLEM: Function was called but no folders created")
    print("   Check debug log for errors")
else:
    print("✓ SUCCESS: Function was called and folders created")

print("\n" + "=" * 80)
