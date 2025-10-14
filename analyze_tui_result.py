"""
TUI 실행 후 결과만 확인하는 스크립트
사용자가 TUI를 직접 실행한 후 이 스크립트로 결과를 확인합니다.
"""
from pathlib import Path
from datetime import datetime
import json

print("=" * 80)
print("TUI 실행 결과 분석")
print("=" * 80)
print(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 1. Debug log 확인
print("[1] 디버그 로그 분석")
print("-" * 80)
debug_log = Path("out/session_creation_debug.log")
if debug_log.exists():
    print(f"✓ 로그 존재 ({debug_log.stat().st_size} bytes)\n")
    content = debug_log.read_text(encoding="utf-8")
    
    # 최신 온보딩 로그만 추출
    lines = content.split('\n')
    onboarding_start = -1
    for i, line in enumerate(lines):
        if '=== ONBOARDING EXCEL STAGE ===' in line:
            onboarding_start = i
    
    if onboarding_start >= 0:
        print("📋 최근 온보딩 로그:")
        for line in lines[onboarding_start:]:
            if line.strip():
                print(f"  {line}")
    else:
        print("⚠️  온보딩 Excel 단계 로그가 없습니다!")
        print("   전체 로그:")
        for line in lines[-20:]:  # 마지막 20줄만
            if line.strip():
                print(f"  {line}")
else:
    print("❌ 디버그 로그가 없습니다!")
    print("   → _create_session_excel_and_fill() 함수가 호출되지 않았습니다.")

# 2. Sessions 확인
print("\n[2] 세션 디렉터리 분석")
print("-" * 80)
sessions_dir = Path("out/sessions")
if sessions_dir.exists():
    items = list(sessions_dir.iterdir())
    folders = [i for i in items if i.is_dir()]
    files = [i for i in items if i.is_file() and i.suffix == '.json']
    
    print(f"총 항목: {len(items)}개")
    print(f"  - 세션 폴더: {len(folders)}개")
    print(f"  - 스냅샷 파일: {len(files)}개\n")
    
    if folders:
        print("📁 세션 폴더 목록:")
        for i, folder in enumerate(sorted(folders, key=lambda x: x.stat().st_mtime, reverse=True), 1):
            mtime = datetime.fromtimestamp(folder.stat().st_mtime)
            print(f"  {i}. {folder.name}/")
            print(f"     생성 시간: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            sub_items = list(folder.iterdir())
            print(f"     파일 개수: {len(sub_items)}개")
            for sub in sorted(sub_items)[:3]:  # 처음 3개만
                size = sub.stat().st_size if sub.is_file() else 0
                print(f"       - {sub.name} ({size:,} bytes)")
            if len(sub_items) > 3:
                print(f"       ... 외 {len(sub_items) - 3}개")
    else:
        print("❌ 세션 폴더가 없습니다!")
        print("   → 세션 생성이 실패했거나 호출되지 않았습니다.")
    
    if files:
        print("\n📄 세션 스냅샷 목록:")
        for i, file in enumerate(sorted(files, key=lambda x: x.stat().st_mtime, reverse=True), 1):
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            print(f"  {i}. {file.name}")
            print(f"     생성 시간: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                print(f"     target_module: {data.get('target_module', 'N/A')}")
                excel_path = data.get('excel_path', 'N/A')
                if excel_path != 'N/A':
                    print(f"     excel_path: {Path(excel_path).name}")
                
                session_excel = data.get('session_excel_path', '')
                if session_excel:
                    print(f"     session_excel_path: ✅ {Path(session_excel).name}")
                else:
                    print(f"     session_excel_path: ❌ EMPTY (세션 생성 안됨!)")
            except Exception as e:
                print(f"     오류: {e}")
    else:
        print("\n⚠️  세션 스냅샷이 없습니다.")
else:
    print("❌ 세션 디렉터리가 없습니다!")

# 3. 진단
print("\n[3] 진단 결과")
print("-" * 80)

has_log = debug_log.exists()
has_onboarding_log = False
if has_log:
    content = debug_log.read_text(encoding="utf-8")
    has_onboarding_log = '=== ONBOARDING EXCEL STAGE ===' in content

has_folders = len(folders) > 0 if sessions_dir.exists() and 'folders' in locals() else False
has_valid_snapshot = False
if sessions_dir.exists() and 'files' in locals() and files:
    try:
        latest_snap = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        data = json.loads(latest_snap.read_text(encoding="utf-8"))
        has_valid_snapshot = bool(data.get('session_excel_path', ''))
    except:
        pass

if has_folders and has_valid_snapshot:
    print("✅ 정상: 세션이 성공적으로 생성되었습니다!")
    print("   - 세션 폴더 존재")
    print("   - session_excel_path 설정됨")
elif has_onboarding_log and not has_folders:
    print("⚠️  부분 실패: 온보딩은 시도했으나 세션 폴더가 없습니다.")
    print("   → 디버그 로그를 확인하여 실패 원인을 파악하세요.")
elif not has_onboarding_log:
    print("❌ 실패: 온보딩 Excel 단계까지 도달하지 못했습니다.")
    print("\n가능한 원인:")
    print("  1. RTL 경로 입력 단계에서 문제 발생")
    print("  2. 모듈 선택 단계에서 문제 발생")
    print("  3. Excel 단계 이전에 종료됨")
    print("\n해결 방법:")
    print("  - TUI를 다시 실행하고 각 단계를 정확히 완료하세요")
    print("  - RTL 경로: EDA/RTL")
    print("  - 모듈: 9")
    print("  - Excel: 그냥 Enter (자동 감지)")
else:
    print("❌ 실패: 원인 불명")
    print("   디버그 로그를 확인하세요.")

print("\n" + "=" * 80)
print("💡 TIP: 자동화 테스트를 원하면 'python run_automated_test.py' 실행")
print("=" * 80)
