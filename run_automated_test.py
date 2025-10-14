"""
Automated TUI Testing Script
자동으로 온보딩을 수행하고 결과를 분석합니다.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

print("=" * 80)
print("AUTOMATED TUI ONBOARDING TEST")
print("=" * 80)
print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Step 1: Preparation
print("[1/6] 준비 중...")
print("      - 디버그 로그 초기화")
print("      - 세션 디렉터리 정리")

debug_log = Path("out/session_creation_debug.log")
if debug_log.exists():
    debug_log.unlink()

import shutil
sessions_dir = Path("out/sessions")
if sessions_dir.exists():
    for item in sessions_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

print("      ✓ 준비 완료\n")
time.sleep(0.5)

# Step 2: Import modules
print("[2/6] 모듈 로딩 중...")
print("      - cli_tui 모듈")
print("      - rtl_parser 모듈")

try:
    from cli_tui import (
        AppState, 
        _create_session_excel_and_fill,
        _save_session_snapshot,
        build_context_from_rtl,
        _auto_find_excel
    )
    print("      ✓ 모듈 로딩 완료\n")
except Exception as e:
    print(f"      ✗ 모듈 로딩 실패: {e}\n")
    sys.exit(1)

time.sleep(0.5)

# Step 3: Initialize state
print("[3/6] 상태 초기화 중...")
state = AppState()
state.rtl_start = Path("EDA/RTL").resolve()
print(f"      - RTL 경로: {state.rtl_start}")
print("      ✓ 상태 초기화 완료\n")
time.sleep(0.5)

# Step 4: Build RTL context
print("[4/6] RTL 분석 중...")
print("      - RTL 파일 스캔")
print("      - 모듈 정보 추출")

try:
    modules, mi, occs = build_context_from_rtl(state.rtl_start, None)
    state.modules_db = modules
    state.module_info = mi
    state.occs = occs
    
    module_list = sorted(modules.keys())
    print(f"      - 발견된 모듈: {len(module_list)}개")
    
    # Select module #9 (index 8)
    if len(module_list) > 8:
        state.target_module = module_list[8]
        print(f"      - 선택된 모듈: {state.target_module}")
        
        # Refresh module_info
        modules, mi, occs = build_context_from_rtl(state.rtl_start, state.target_module)
        state.modules_db = modules
        state.module_info = mi
        state.occs = occs
        print(f"      - 입력 포트: {len(mi.inputs)}개")
        print(f"      - 출력 포트: {len(mi.outputs)}개")
        print("      ✓ RTL 분석 완료\n")
    else:
        print(f"      ✗ 모듈이 충분하지 않습니다 (발견: {len(module_list)}개)\n")
        sys.exit(1)
        
except Exception as e:
    print(f"      ✗ RTL 분석 실패: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

time.sleep(0.5)

# Step 5: Find Excel
print("[5/6] Excel 파일 검색 중...")
print("      - Data 디렉터리 스캔")

excel_found = _auto_find_excel()
if excel_found:
    state.excel_path = excel_found
    state.onboarding_excel_autofound = excel_found
    print(f"      - 발견된 Excel: {excel_found.name}")
    print("      ✓ Excel 검색 완료\n")
else:
    print("      ✗ Excel 파일을 찾을 수 없습니다\n")
    sys.exit(1)

time.sleep(0.5)

# Step 6: Create session
print("[6/6] 세션 생성 중...")
print("      - 세션 디렉터리 생성")
print("      - Excel 파일 복사")
print("      - Define 시트 준비")

print(f"\n      [DEBUG] cmdline = '' (empty)")
print(f"      [DEBUG] not cmdline = {not ''}")
print(f"      [DEBUG] autofound = {state.onboarding_excel_autofound}")
print(f"      [DEBUG] Condition: {not '' and state.onboarding_excel_autofound}\n")

state.onboarding_active = False
state.onboarding_stage = None

ok, err = _create_session_excel_and_fill(state)

print(f"\n      결과: {'성공' if ok else '실패'}")
if ok:
    print(f"      메시지: {err}")
    print(f"      세션 Excel: {state.session_excel_path}")
    print("      ✓ 세션 생성 완료\n")
    
    # Save snapshot
    print("      - 세션 스냅샷 저장 중...")
    _save_session_snapshot(state)
    print("      ✓ 스냅샷 저장 완료\n")
else:
    print(f"      오류: {err}\n")

time.sleep(0.5)

# Results
print("=" * 80)
print("결과 분석")
print("=" * 80)

# Check debug log
print("\n[디버그 로그]")
if debug_log.exists():
    content = debug_log.read_text(encoding="utf-8")
    print(f"✓ 로그 파일 존재 ({debug_log.stat().st_size} bytes)")
    print("\n내용:")
    for line in content.split('\n'):
        print(f"  {line}")
else:
    print("✗ 로그 파일 없음 - 함수가 호출되지 않았습니다!")

# Check sessions
print("\n[세션 디렉터리]")
if sessions_dir.exists():
    items = list(sessions_dir.iterdir())
    folders = [i for i in items if i.is_dir()]
    files = [i for i in items if i.is_file()]
    
    print(f"총 항목: {len(items)}개")
    print(f"  - 폴더: {len(folders)}개")
    print(f"  - 파일: {len(files)}개")
    
    if folders:
        print("\n📁 세션 폴더:")
        for folder in sorted(folders, key=lambda x: x.stat().st_mtime, reverse=True):
            print(f"  ✓ {folder.name}/")
            for sub in sorted(folder.iterdir()):
                size = sub.stat().st_size if sub.is_file() else 0
                print(f"      - {sub.name} ({size:,} bytes)")
    else:
        print("\n✗ 세션 폴더가 생성되지 않았습니다!")
    
    if files:
        print("\n📄 세션 스냅샷:")
        for file in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
            import json
            data = json.loads(file.read_text(encoding="utf-8"))
            print(f"  - {file.name}")
            print(f"      target_module: {data.get('target_module', 'N/A')}")
            session_excel = data.get('session_excel_path', '')
            if session_excel:
                print(f"      session_excel_path: ✓ {Path(session_excel).name}")
            else:
                print(f"      session_excel_path: ✗ EMPTY")
else:
    print("✗ 세션 디렉터리가 없습니다!")

# Final verdict
print("\n" + "=" * 80)
print("최종 결과")
print("=" * 80)

if ok and state.session_excel_path and folders:
    print("\n✅ 성공! 세션이 정상적으로 생성되었습니다.")
    print(f"   세션 Excel: {state.session_excel_path}")
else:
    print("\n❌ 실패! 세션 생성에 문제가 있습니다.")
    
    if not debug_log.exists():
        print("   원인: _create_session_excel_and_fill() 함수가 호출되지 않았습니다.")
    elif not folders:
        print("   원인: 세션 폴더가 생성되지 않았습니다.")
    elif not state.session_excel_path:
        print("   원인: session_excel_path가 설정되지 않았습니다.")

print(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
