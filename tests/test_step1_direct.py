#!/usr/bin/env python3
"""
TUI Step 1 onboarding 직접 테스트 (curses 없이)
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from rtl_parser import (
    discover_files,
    find_rtl_root_from,
    build_modules_db,
    find_module_instances_by_file,
)

# ModuleInfo 정의 (cli_tui.py에서 복사)
@dataclass
class ModuleInfo:
    module: str = ""
    rtl_file_path: str = ""
    module_hierarchy: str = ""
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    inouts: List[Dict[str, Any]] = field(default_factory=list)
    clocks: List[Dict[str, Any]] = field(default_factory=list)
    resets: List[Dict[str, Any]] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)

# AppState 정의 (cli_tui.py에서 복사 - 최소 버전)
@dataclass
class AppState:
    rtl_start: Optional[Path] = None
    target_module: Optional[str] = None
    modules_db: Dict[str, Any] = field(default_factory=dict)
    module_info: ModuleInfo = field(default_factory=ModuleInfo)
    onboarding_active: bool = True
    onboarding_stage: str = 'rtl'
    onboarding_modules: List[str] = field(default_factory=list)
    onboarding_instances: List[Dict[str, Any]] = field(default_factory=list)

# 테스트
print("=" * 80)
print("Direct Test: TUI Step 1 Processing")
print("=" * 80)
print()

state = AppState()
_THIS_DIR = Path(__file__).resolve().parent

# Step 1 명령어 시뮬레이션: sync_signal.v 선택
cmdline = "EDA/RTL/sync_signal.v"
p = Path(cmdline).expanduser().resolve()

print(f"Input file: {p}")
print(f"File exists: {p.exists()}")
print()

if not p.exists():
    print("ERROR: File not found!")
    sys.exit(1)

# Step 1 로직 재현
try:
    # DEBUG LOG 파일 설정
    debug_log_file = _THIS_DIR / "out" / "tui_step1_debug.log"
    debug_log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_debug(msg):
        with open(debug_log_file, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")
        print(f"  LOG: {msg}")
    
    # 로그 파일 초기화
    debug_log_file.write_text("=== TUI Step 1 Debug Log ===\n", encoding="utf-8")
    log_debug(f"Processing RTL file: {p}")
    
    # 1. 전체 모듈 데이터베이스 구축
    rtl_root, _found = find_rtl_root_from(p)
    start_scope_dir = p if p.is_dir() else p.parent
    files = sorted(set(discover_files(rtl_root, [".v", ".sv"])) | set(discover_files(start_scope_dir, [".v", ".sv"])), key=lambda f: str(f))
    log_debug(f"Files discovered: {len(files)}")
    
    mods_ctx = build_modules_db(files, allow_unknown=True)
    state.modules_db = mods_ctx
    log_debug(f"Modules parsed: {len(mods_ctx)}")
    
    # 2. 인스턴스 찾기
    log_debug("Calling find_module_instances_by_file...")
    file_modules_hierarchy = find_module_instances_by_file(mods_ctx, p)
    log_debug(f"Instances found: {len(file_modules_hierarchy)}")
    
    # 3. 파일에 정의된 모듈 확인
    file_modules_defined = [name for name, m in mods_ctx.items() if Path(m["file"]).resolve() == p.resolve()]
    log_debug(f"Modules in file: {file_modules_defined}")
    
    # 4. 인스턴스 디테일 출력
    print("\n" + "=" * 80)
    print("DETAILED HIERARCHY PATHS:")
    print("=" * 80)
    for idx, inst in enumerate(file_modules_hierarchy, 1):
        print(f"\n[{idx}] Instance Name: {inst.get('display', inst['hierarchy_path'])}")
        print(f"    Hierarchy Path: {inst['hierarchy_path']}")
        print(f"    File Module: {inst['file_module']}")
        print(f"    Complete: {'.' in inst['hierarchy_path']}")
    
    # 5. Step 2 상태 설정
    
    # 인스턴스 검증
    if not file_modules_hierarchy:
        log_debug("ERROR: No instances found!")
        print("\n❌ ERROR: No instances found!")
        sys.exit(1)
    
    # 계층 구조 처리
    instances = []
    for item in file_modules_hierarchy:
        hierarchy = item["hierarchy_path"]
        file_module = item["file_module"]
        log_debug(f"Processing instance: {hierarchy} (module: {file_module})")
        instances.append({
            "file_module": file_module,
            "hierarchy": hierarchy,
            "display": hierarchy,
            "chain": item["instance_chain"],
        })
    
    instances.sort(key=lambda x: x["hierarchy"])
    log_debug(f"Total instances after sorting: {len(instances)}")
    
    state.onboarding_instances = instances
    state.onboarding_modules = [inst["display"] for inst in instances]
    log_debug(f"state.onboarding_modules set to: {state.onboarding_modules}")
    
    print("\n" + "=" * 80)
    print("RESULT: Step 2 would display:")
    print("=" * 80)
    for i, mod in enumerate(state.onboarding_modules, 1):
        print(f"[{i}] {mod}")
    
    print(f"\nDebug log saved to: {debug_log_file}")
    
except Exception as e:
    import traceback
    print(f"\n❌ EXCEPTION: {e}")
    print(traceback.format_exc())
    sys.exit(1)
