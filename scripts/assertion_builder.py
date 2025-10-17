#!/usr/bin/env python3
"""
Unified, modular assertion builder.

Features:
- RTL scan using scripts/rtl_parser.py internal APIs to extract ports for a target module.
- Define Excel population (reuses scripts/fill_define.py logic via JSON handoff).
- Extensible assertion plugins (see scripts/assertions/*) for each Excel sheet type.
- Configurable inputs via CLI or optional config file.

Quick start:
  python scripts/assertion_builder.py \
    --rtl-start EDA/RTL \
    --target-module blur_scaler \
    --excel Data/Assertion_TF.xlsx \
    --auto-define-fill \
    --out out/assertions

No-args interactive mode:
- Run without options to launch an interactive wizard that lets you pick
  RTL start path, target module, Excel file from Data/, plugins, and modes
  (Define fill, JSON output, SV generation).

Adding new assertion sheet:
- Create a plugin under scripts/assertions (see base.py and counter.py).
- Implement parse/generate_sv, register in registry.
- Run with --enable <plugin_name> or leave enabled by default.

Assistant prompt hint to extend:
- "Add a plugin 'sequence' for sheet 'sequence_gen' with headers ... that
    emits sequence ..." The AI should add scripts/assertions/sequence.py
    inheriting BaseAssertionPlugin and update registry.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import re
from pathlib import Path
import platform
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type
import os
import importlib

# Make local 'scripts' directory importable no matter the CWD
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

# Import RTL parsing helpers from scripts/rtl_parser.py (as a library)
from rtl_parser import (  # type: ignore
    discover_files,
    find_rtl_root_from,
    build_modules_db,
    find_top_modules,
    find_occurrences_of_target,
    compute_env_for_occurrence,
    resolve_ports_with_params,
    classify_groups,
)

from assertions import get_registered_plugins, BaseAssertionPlugin  # type: ignore


def _run_pip_install(packages: List[str]) -> Tuple[bool, str]:
    """Attempt to install given pip packages non-interactively. Returns (ok, output)."""
    if not packages:
        return True, ""
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
    ] + packages
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out
    except Exception as e:
        return False, f"pip failed: {e}"


def _ensure_runtime_deps(require_tui: bool) -> None:
    """
    Ensure required Python dependencies are available. If missing, try to install.
    - Always checks: pandas, openpyxl (used by plugins/fill scripts)
    - If require_tui: also ensure curses (windows-curses on Windows)
    Fails with SystemExit if a required package cannot be installed.
    """
    missing: List[str] = []

    # Core Excel stack
    try:
        import pandas  # type: ignore  # noqa: F401
    except Exception:
        missing.append("pandas")
    try:
        import openpyxl  # type: ignore  # noqa: F401
    except Exception:
        missing.append("openpyxl")

    # TUI dependency
    win_needs_curses = False
    if require_tui:
        try:
            import curses  # type: ignore  # noqa: F401
        except Exception:
            if platform.system() == "Windows":
                # On Windows, the shim package provides _curses
                missing.append("windows-curses")
                win_needs_curses = True
            else:
                # On non-Windows, curses should be in stdlib; if not, abort
                raise SystemExit("curses module not available; cannot launch TUI")

    if missing:
        ok, out = _run_pip_install(missing)
        if not ok:
            print(out)
            raise SystemExit(f"Failed to install required packages: {', '.join(missing)}")

    # Verify imports after install
    try:
        import pandas  # type: ignore  # noqa: F401
        import openpyxl  # type: ignore  # noqa: F401
    except Exception as e:
        raise SystemExit(f"Dependencies not satisfied after install attempt: {e}")

    if require_tui:
        try:
            import curses  # type: ignore  # noqa: F401
        except Exception as e:
            if win_needs_curses:
                raise SystemExit("windows-curses installed but curses still unavailable; cannot launch TUI")
            raise SystemExit(f"curses unavailable: {e}")


def build_module_context(rtl_start: Path, target_module: Optional[str]) -> Dict[str, Any]:
    exts = [".v", ".sv"]
    rtl_root, found = find_rtl_root_from(rtl_start)
    start_scope_dir = rtl_start if rtl_start.is_dir() else rtl_start.parent
    files = sorted(set(discover_files(rtl_root, exts)) | set(discover_files(start_scope_dir, exts)), key=lambda p: str(p))
    # tb_top 등 Non-ANSI 전용 파일 제외
    files = _filter_rtl_ansi(files)
    modules = build_modules_db(files, allow_unknown=False)
    if not modules:
        raise SystemExit("No modules parsed from RTL scope")

    if not target_module:
        tops = find_top_modules(modules)
        # Fallback: pick the first top as target
        target_module = tops[0] if tops else next(iter(modules.keys()))

    # Resolve first occurrence for environment
    occs = find_occurrences_of_target(modules, target_module)
    env = compute_env_for_occurrence(occs[0], modules, {}) if occs else {}
    ports_resolved = resolve_ports_with_params(modules, target_module, env)
    cls = classify_groups(modules[target_module]["ports"])
    # Exclude clock/reset names from inputs
    ex_names = {x["name"] for x in cls.get("clocks", [])} | {x["name"] for x in cls.get("resets", [])}
    inputs_filtered = [it for it in ports_resolved["inputs"] if it["name"] not in ex_names]

    module_info = {
        "module": target_module,
        "inputs": inputs_filtered,
        "outputs": ports_resolved["outputs"],
        "inouts": ports_resolved["inouts"],
        "clocks": cls.get("clocks", []),
        "resets": cls.get("resets", []),
        "parameters": cls.get("parameters", []),
    }
    return {"modules": modules, "module_info": module_info, "occs": occs}


def fill_define_excel_if_needed(excel_path: Path, module_info: Dict[str, Any], out_json_dir: Path):
    out_json_dir.mkdir(parents=True, exist_ok=True)
    define_json_path = out_json_dir / "module_define.json"
    define_json = {
        "top_path": "",
        "module": module_info["module"],
        "rtl_file_path": module_info.get("rtl_file_path", ""),  # Add RTL file path
        "paths": [],
        "instances": [],
        "clocks": module_info["clocks"],
        "resets": module_info["resets"],
        "inputs": module_info["inputs"],
        "outputs": module_info["outputs"],
        "inouts": module_info["inouts"],
        "parameters": module_info["parameters"],
        "conditions": module_info.get("conditions", []),  # Add condition signals
    }
    define_json_path.write_text(json.dumps(define_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # Reuse the fill_define.py script via import and call its main logic? It is CLI-oriented.
    # For simplicity and to avoid tight coupling, invoke it as a subprocess-like call would be ideal,
    # but here we keep it as an external step. The caller can run:
    #   python scripts/fill_define.py <excel_path> <define_json_path>
    return define_json_path


def _create_session_excel_copy(reference_excel: Path, target_module: str, out_dir: Path) -> Tuple[Path, Path]:
    """
    Reference 엑셀을 세션 폴더로 복사하고 구조화된 디렉터리를 생성합니다.
    
    Args:
        reference_excel: 원본 엑셀 파일 경로
        target_module: 대상 모듈명
        out_dir: 출력 디렉터리 (일반적으로 out/assertions)
    
    Returns:
        (session_excel_path, session_dir): 복사된 엑셀 경로와 세션 디렉터리 경로
    """
    # 세션 디렉터리: out/sessions/<module>-<timestamp>/
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"{target_module}-{ts}"
    session_dir = out_dir.parent / "sessions" / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # 엑셀 파일명: <module>.xlsx
    dest_excel = session_dir / f"{target_module}.xlsx"
    
    try:
        shutil.copy2(reference_excel, dest_excel)
        print(f"✓ Session Excel created: {dest_excel}")
        print(f"✓ Session directory: {session_dir}")
        return dest_excel, session_dir
    except Exception as e:
        print(f"[Warn] Failed to copy Excel: {e}")
        print(f"[Info] Using reference Excel directly: {reference_excel}")
        return reference_excel, out_dir


# ANSI/Non-ANSI 모듈 헤더 정규식 및 필터 유틸 추가
_ANSI_MOD_RE = re.compile(r"(?ims)^\s*module\s+[A-Za-z_]\w*\s*(?:#\s*\(.*?\)\s*)?\(")
_NONANSI_MOD_RE = re.compile(r"(?im)^\s*module\s+[A-Za-z_]\w*\s*(?:#\s*\(.*?\)\s*)?;")

def _read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _filter_rtl_ansi(files: List[Path]) -> List[Path]:
    """포트 리스트가 있는 ANSI 헤더 포함 파일만 통과. Non-ANSI만 있는 파일은 제외."""
    out: List[Path] = []
    skipped = 0
    for p in files:
        if p.suffix.lower() not in (".v", ".sv"):
            continue
        txt = _read_text_safe(p)
        if _ANSI_MOD_RE.search(txt):
            out.append(p)
            continue
        if _NONANSI_MOD_RE.search(txt):
            skipped += 1
            continue
    if skipped:
        print(f"[Info] Skipped {skipped} Non-ANSI module header file(s) during RTL scan")
    return out


def run_builder(
    rtl_start: Path,
    target_module: Optional[str],
    excel_path: Path,
    out_dir: Path,
    auto_define_fill: bool,
    enabled_plugins: Optional[List[str]],
    emit_json: bool,
    handshake_cfg: Optional[Dict[str, str]] = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_module_context(rtl_start, target_module)
    module_info = ctx["module_info"]
    actual_module = module_info["module"]
    
    # Handshake 타입을 플러그인에 전달(환경변수로 기본값 주입)
    if handshake_cfg and handshake_cfg.get("force_type"):
        os.environ["ASSERTION_FORCE_TYPE"] = handshake_cfg["force_type"]

    # Reference 엑셀을 세션용으로 복사
    session_excel, session_dir = _create_session_excel_copy(excel_path, actual_module, out_dir)

    # Optionally emit JSON for Define sheet population
    if auto_define_fill:
        # JSON을 세션 디렉터리에 생성
        define_json_path = fill_define_excel_if_needed(session_excel, module_info, session_dir)
        print(f"✓ Define JSON written: {define_json_path}")
        # Auto-run fill_define.py to populate the Excel Define sheet
        fill_script = _THIS_DIR / "fill_define.py"
        if fill_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, "-X", "utf8", str(fill_script), str(session_excel), str(define_json_path)],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1"),
                )
                if result.returncode == 0:
                    print("✓ Define sheet populated successfully")
                else:
                    print("[Warn] fill_define.py execution failed")
                    if result.stdout:
                        print(result.stdout.strip()[-500:])
                    if result.stderr:
                        print(result.stderr.strip()[-500:])
            except Exception as e:
                print(f"[Warn] fill_define.py execution failed: {e}")
        else:
            print("[Info] scripts/fill_define.py not found; please run it manually.")

    # Load enabled plugins
    plugin_types: List[Type[BaseAssertionPlugin]] = get_registered_plugins()
    if enabled_plugins:
        enabled_names = set(enabled_plugins)
        plugin_types = [p for p in plugin_types if p.plugin_name in enabled_names]

    # Parse Excel sheets via plugins (세션 엑셀 사용)
    parsed_by_plugin: Dict[str, Dict[str, Any]] = {}
    for pcls in plugin_types:
        try:
            parsed_by_plugin[pcls.plugin_name] = pcls().parse(session_excel)
        except Exception as e:
            print(f"[Warn] Plugin {pcls.plugin_name} parse failed: {e}")

    # Emit consolidated JSON (ports + per-plugin parsed structures)
    if emit_json:
        json_blob = {
            "module": module_info["module"],
            "clocks": module_info["clocks"],
            "resets": module_info["resets"],
            "inputs": module_info["inputs"],
            "outputs": module_info["outputs"],
            "inouts": module_info["inouts"],
            "parameters": module_info["parameters"],
            "sheets": parsed_by_plugin,
        }
        # JSON도 세션 디렉터리에 저장
        json_path = session_dir / "assertion_inputs.json"
        json_path.write_text(json.dumps(json_blob, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ Inputs JSON written: {json_path}")

    # 공통 컨텍스트(plugins generate_sv 호출 전에 필요)
    common_context = {
        "module_info": module_info,
        "define_excel_path": str(session_excel),
        "output_dir": str(session_dir),
        "session_dir": str(session_dir),
        "config": {
            "auto_define_fill": True,
            "enabled_plugins": enabled_plugins,
            "emit_json": True,
        },
    }

    # 3) SV 생성 (항상)
    sv_sections: List[str] = []
    for pcls in plugin_types:
        parsed = parsed_by_plugin.get(pcls.plugin_name)
        if not parsed:
            continue
        try:
            sv_sections.extend(pcls().generate_sv(parsed, common_context))
        except Exception as e:
            print(f"[Warn] Plugin {pcls.plugin_name} generate failed: {e}")

    print(f"\n===== Outputs saved to: {session_dir} =====")


def _prompt(msg: str, default: Optional[str] = None) -> str:
    hint = f" [{default}]" if default else ""
    s = input(f"{msg}{hint}: ").strip()
    return s or (default or "")


def _pick_one(title: str, options: List[Tuple[str, str]], allow_custom: bool = False) -> str:
    print(title)
    for i, (label, _) in enumerate(options, start=1):
        print(f"  [{i}] {label}")
    if allow_custom:
        print("  [0] Enter custom path")
    while True:
        s = input("Select > ").strip()
        if allow_custom and s == "0":
            return _prompt("Enter custom path")
        if s.isdigit():
            i = int(s)
            if 1 <= i <= len(options):
                return options[i-1][1]
        print("Invalid selection. Try again.")


def _pick_multi(title: str, options: List[str]) -> List[str]:
    print(title)
    for i, label in enumerate(options, start=1):
        print(f"  [{i}] {label}")
    print("Enter numbers separated by space/comma (or 'all').")
    while True:
        s = input("Select > ").strip().lower()
        if s in ("all", "a"):
            return list(options)
        toks = [t for t in s.replace(",", " ").split() if t.isdigit()]
        picks: List[str] = []
        for t in toks:
            i = int(t)
            if 1 <= i <= len(options):
                picks.append(options[i-1])
        if picks:
            return picks
        print("Invalid selection. Try again.")


def interactive_wizard():
    print("==== Assertion Builder Interactive Mode ====")
    repo_root = _THIS_DIR.parent

    # RTL start candidates
    candidates: List[Tuple[str, str]] = []
    eda_rtl = repo_root / "EDA" / "RTL"
    if eda_rtl.exists():
        candidates.append((f"{eda_rtl} (EDA/RTL)", str(eda_rtl.resolve())))
    # Scan for other 'RTL' dirs (limit to 10)
    found = []
    try:
        for p in repo_root.rglob("RTL"):
            if p.is_dir() and p != eda_rtl:
                found.append(p)
                if len(found) >= 10:
                    break
    except Exception:
        pass
    for p in found:
        candidates.append((str(p), str(p.resolve())))
    if not candidates:
        candidates.append((str(repo_root), str(repo_root.resolve())))
    rtl_start_str = _pick_one("Select RTL start directory", candidates, allow_custom=True)
    rtl_start = Path(rtl_start_str).resolve()

    # Build modules DB to offer module selection
    try:
        ctx = build_module_context(rtl_start, None)
        modules = ctx["modules"]
    except SystemExit as e:
        print(str(e))
        sys.exit(1)

    mod_names = sorted(list(modules.keys()))
    # Prefer tops at front
    tops = set(find_top_modules(modules))
    mod_names_sorted = sorted(mod_names, key=lambda m: (0 if m in tops else 1, m))
    target_module = _pick_one("Select target module", [(m, m) for m in mod_names_sorted])

    # Excel selection from Data/
    data_dir = repo_root / "Data"
    excel_opts: List[Tuple[str, str]] = []
    if data_dir.exists():
        for x in sorted(data_dir.glob("*.xlsx")):
            if x.name.startswith("~$"):
                continue
            excel_opts.append((x.name, str(x.resolve())))
    if not excel_opts:
        excel_path = Path(_prompt("Enter Excel file path"))
    else:
        excel_path_str = _pick_one("Select Excel file (Data/)", excel_opts, allow_custom=True)
        excel_path = Path(excel_path_str).resolve()

    # Remove Output directory prompt; set default silently
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = (repo_root / "out" / "assertions").resolve()

    # 모드 프롬프트 제거: 항상 1/2/3 모두 수행
    auto_define_fill = True
    emit_json = True

    # Plugin selection
    _import_all_plugins()
    plugin_types = get_registered_plugins()
    plugin_names = [p.plugin_name for p in plugin_types]
    enabled = _pick_multi("Select plugins (or 'all')", plugin_names)

    # handshake 플러그인이 포함되면 ready_valid까지 포함한 타입을 미리 선택(플러그인 기본값으로 전달)
    handshake_cfg = {}
    if "handshake" in enabled:
        hs_type = _pick_one("Select handshake type (2phase/4phase/ready_valid)",
                            [("2phase", "2phase"), ("4phase", "4phase"), ("ready_valid", "ready_valid")])
        handshake_cfg = {"force_type": hs_type}

    return {
        "rtl_start": rtl_start,
        "target_module": target_module,
        "excel_path": excel_path,
        "out_dir": out_dir,
        "auto_define_fill": auto_define_fill,
        "enabled_plugins": enabled,
        "emit_json": emit_json,
        "handshake_cfg": handshake_cfg,
    }


def _import_all_plugins() -> None:
    """
    scripts/assertions 폴더 내의 모든 플러그인 모듈을 동적 import하여
    @register 데코레이터가 실행되도록 보장합니다.
    """
    pkg_dir = _THIS_DIR / "assertions"
    pkg_name = "assertions"
    if not pkg_dir.exists():
        return
    for py in pkg_dir.glob("*.py"):
        name = py.stem
        if name in ("__init__", "base", "registry"):
            continue
        mod_name = f"{pkg_name}.{name}"
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            print(f"[Warn] Failed to import plugin {name}: {e}")


def main():
    # Default: launch TUI when no args
    if len(sys.argv) == 1:
        try:
            _ensure_runtime_deps(require_tui=True)
            from cli_tui import run as run_tui  # type: ignore
        except Exception as e:
            print(f"[Info] TUI failed to start ({e}); falling back to wizard.")
            cfg = interactive_wizard()
            return run_builder(**cfg)
        return run_tui()

    parser = argparse.ArgumentParser(description="Modular Assertion Builder")
    parser.add_argument("--rtl-start", help="Start path (file or dir) to scan RTL")
    parser.add_argument("--target-module", help="Target module name (optional)")
    parser.add_argument("--excel", help="Reference Excel path containing sheets")
    parser.add_argument("--out", default="out/assertions", help="Output directory for generated files")
    parser.add_argument("--auto-define-fill", action="store_true", help="Produce Define JSON for fill_define.py and log path")
    parser.add_argument("--use-default-excel", action="store_true", help="Ignore --excel and use default Data/Assertion_TF.xlsx")
    parser.add_argument("--enable", action="append", help="Enable only listed plugins (name). Can repeat.")
    parser.add_argument("--json", action="store_true", help="Emit consolidated JSON of inputs/outputs/parameters")
    parser.add_argument("--tui", action="store_true", help="Launch full-screen TUI")
    parser.add_argument("--wizard", action="store_true", help="Launch interactive wizard instead of TUI")
    args = parser.parse_args()

    # Explicit TUI launch
    if getattr(args, "tui", False) and not getattr(args, "wizard", False):
        _ensure_runtime_deps(require_tui=True)
        from cli_tui import run as run_tui  # type: ignore
        return run_tui()

    # Explicit wizard
    if getattr(args, "wizard", False):
        cfg = interactive_wizard()
        return run_builder(**cfg)

    # Validate required when not interactive
    _ensure_runtime_deps(require_tui=False)
    if not args.rtl_start:
        raise SystemExit("--rtl-start is required when not using interactive mode")
    # Excel path selection with optional default
    if args.use_default_excel:
        excel_path = Path("Data/Assertion_TF.xlsx").resolve()
    else:
        if not args.excel:
            raise SystemExit("--excel is required when not using interactive mode (or use --use-default-excel)")
        excel_path = Path(args.excel).resolve()

    run_builder(
        rtl_start=Path(args.rtl_start).resolve(),
        target_module=args.target_module,
        excel_path=excel_path,
        out_dir=Path(args.out).resolve(),
        auto_define_fill=bool(args.auto_define_fill),
        enabled_plugins=list(args.enable) if args.enable else None,
        emit_json=bool(args.json),
        handshake_cfg=None,
    )


if __name__ == "__main__":
    main()


