#!/usr/bin/env python3
"""
new 명령어 직접 테스트
"""
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import shutil

# Add scripts to path
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR / "scripts"))

print("=" * 80)
print("new 명령어 실행 시뮬레이션")
print("=" * 80)

# ModuleInfo mock
@dataclass
class ModuleInfo:
    module: str = ""
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    inouts: List[Dict[str, Any]] = field(default_factory=list)
    clocks: List[Dict[str, Any]] = field(default_factory=list)
    resets: List[Dict[str, Any]] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)

# AppState mock
@dataclass
class AppState:
    rtl_start: Optional[Path] = None
    target_module: Optional[str] = None
    excel_path: Optional[Path] = None
    out_dir: Path = Path("out/assertions")
    module_info: ModuleInfo = field(default_factory=ModuleInfo)
    session_excel_path: Optional[Path] = None
    conditions: List[Dict[str, Any]] = field(default_factory=list)

# 1. State 설정
state = AppState()
state.target_module = "out_sync_gen"
state.module_info.module = "out_sync_gen"
state.excel_path = Path("Data/Assertion_TF.xlsx")

print(f"\n초기 상태:")
print(f"  모듈: {state.target_module}")
print(f"  Excel: {state.excel_path}")
print(f"  Session Excel: {state.session_excel_path}")

# 2. 조건 체크
if not state.module_info.module:
    print("\n✗ module_info.module이 없습니다")
    sys.exit(1)

if not state.session_excel_path:
    print("\n✓ session_excel_path가 없으므로 생성 필요")
    
    if not state.excel_path or not state.excel_path.exists():
        print(f"✗ Reference Excel이 없습니다: {state.excel_path}")
        sys.exit(1)
    
    print(f"✓ Reference Excel 존재: {state.excel_path}")
    
    # 3. Session 생성 (간소화)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mod = state.target_module or state.module_info.module
    session_name = f"{mod}-{ts}"
    sess_dir = Path("out/sessions") / session_name
    
    print(f"\n세션 생성:")
    print(f"  이름: {session_name}")
    print(f"  경로: {sess_dir.resolve()}")
    
    try:
        sess_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ 디렉터리 생성됨")
        
        new_xlsx = sess_dir / f"{mod}.xlsx"
        shutil.copy2(state.excel_path, new_xlsx)
        state.session_excel_path = new_xlsx
        print(f"  ✓ Excel 복사: {new_xlsx}")
        
        # JSON 생성
        json_file = sess_dir / "module_define.json"
        json_file.write_text('{"module": "' + mod + '"}', encoding='utf-8')
        print(f"  ✓ JSON 생성: {json_file}")
        
        print(f"\n✓ Session 생성 완료!")
        print(f"  Session Excel: {state.session_excel_path}")
        
    except Exception as e:
        print(f"\n✗ Session 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
else:
    print(f"\n이미 Session Excel이 있습니다: {state.session_excel_path}")

# 4. 결과 확인
print(f"\n{'='*80}")
print(f"최종 상태:")
print(f"{'='*80}")
print(f"  target_module: {state.target_module}")
print(f"  excel_path: {state.excel_path}")
print(f"  session_excel_path: {state.session_excel_path}")

if state.session_excel_path and state.session_excel_path.exists():
    print(f"\n✓ Session Excel 존재 확인됨")
    print(f"  크기: {state.session_excel_path.stat().st_size} bytes")
else:
    print(f"\n✗ Session Excel이 없습니다")
