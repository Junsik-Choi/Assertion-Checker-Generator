#!/usr/bin/env python3
"""
Session 생성 테스트 스크립트
"""
from pathlib import Path
import json

print("=" * 80)
print("Session 생성 상태 확인")
print("=" * 80)

# 1. out/sessions 디렉터리 확인
sessions_dir = Path("out/sessions")
if sessions_dir.exists():
    print(f"\n✓ Sessions 디렉터리 존재: {sessions_dir.resolve()}")
    
    # 세션 폴더 목록
    session_folders = [d for d in sessions_dir.iterdir() if d.is_dir()]
    if session_folders:
        print(f"\n📁 발견된 세션 폴더: {len(session_folders)}개")
        for folder in sorted(session_folders, key=lambda x: x.name)[-5:]:  # 최근 5개만
            print(f"  - {folder.name}")
            
            # Excel 파일 확인
            xlsx_files = list(folder.glob("*.xlsx"))
            if xlsx_files:
                print(f"    ✓ Excel: {xlsx_files[0].name}")
            else:
                print(f"    ✗ Excel 없음")
            
            # JSON 파일 확인
            json_files = list(folder.glob("*.json"))
            if json_files:
                print(f"    ✓ JSON: {', '.join(f.name for f in json_files)}")
            else:
                print(f"    ✗ JSON 없음")
    else:
        print("\n⚠ 세션 폴더가 없습니다")
else:
    print(f"\n✗ Sessions 디렉터리 없음: {sessions_dir.resolve()}")

# 2. Reference Excel 확인
ref_excel = Path("Data/Assertion_TF.xlsx")
if ref_excel.exists():
    print(f"\n✓ Reference Excel 존재: {ref_excel.resolve()}")
else:
    print(f"\n✗ Reference Excel 없음: {ref_excel.resolve()}")

print("\n" + "=" * 80)
print("테스트 완료!")
print("=" * 80)
