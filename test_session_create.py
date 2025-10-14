#!/usr/bin/env python3
"""
Session 생성 직접 테스트
"""
import sys
from pathlib import Path
from datetime import datetime
import shutil

# Add scripts to path
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR / "scripts"))

print("=" * 80)
print("Session 생성 직접 테스트")
print("=" * 80)

# 1. 파라미터 설정
target_module = "out_sync_gen"
reference_excel = Path("Data/Assertion_TF.xlsx")
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
session_name = f"{target_module}-{ts}"
sess_dir = Path("out/sessions") / session_name

print(f"\n설정:")
print(f"  모듈: {target_module}")
print(f"  Reference Excel: {reference_excel}")
print(f"  세션 이름: {session_name}")
print(f"  세션 디렉터리: {sess_dir}")

# 2. Reference Excel 존재 확인
if not reference_excel.exists():
    print(f"\n✗ Reference Excel이 존재하지 않습니다: {reference_excel}")
    sys.exit(1)
else:
    print(f"\n✓ Reference Excel 존재")

# 3. 세션 디렉터리 생성
try:
    sess_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ 세션 디렉터리 생성됨: {sess_dir.resolve()}")
except Exception as e:
    print(f"✗ 세션 디렉터리 생성 실패: {e}")
    sys.exit(1)

# 4. Excel 복사
new_xlsx = sess_dir / f"{target_module}.xlsx"
try:
    shutil.copy2(reference_excel, new_xlsx)
    print(f"✓ Excel 복사 완료: {new_xlsx.resolve()}")
except Exception as e:
    print(f"✗ Excel 복사 실패: {e}")
    sys.exit(1)

# 5. JSON 생성
json_file = sess_dir / "module_define.json"
try:
    json_file.write_text('{"module": "' + target_module + '"}', encoding='utf-8')
    print(f"✓ JSON 생성 완료: {json_file}")
except Exception as e:
    print(f"✗ JSON 생성 실패: {e}")
    sys.exit(1)

# 6. 결과 확인
print(f"\n{'='*80}")
print(f"✓ 세션 생성 완료!")
print(f"{'='*80}")
print(f"\n세션 폴더 내용:")
for item in sorted(sess_dir.iterdir()):
    size = item.stat().st_size if item.is_file() else "-"
    print(f"  {item.name:30s} {str(size):>10s}")

print(f"\n세션 경로: {sess_dir.resolve()}")
