#!/usr/bin/env python3
"""
Full-screen terminal TUI for the Assertion Builder.

Features:
- Fills terminal and adapts to resize.
- Fixed-width grouped panels showing module/IP info, clocks/resets, and ports.
- Command hint line and an input prompt at the bottom.
- Commands: help/h, quit/q, set rtl/module/excel/out, scan, fill, json, sv.
- Integrates with scripts/rtl_parser.py and scripts/assertion_builder.py.

Windows note: requires the 'windows-curses' package: pip install windows-curses
"""

from __future__ import annotations

import os
import sys
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from textwrap import wrap as _textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

# Ensure we can import local scripts
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

try:
    import curses  # type: ignore
except Exception as _curses_err:  # pragma: no cover - import-time environment dependent
    # Provide a clearer error for Windows users
    msg = (
        "Failed to import curses. On Windows, install 'windows-curses' first: "
        "pip install windows-curses\nOriginal error: %r" % (_curses_err,)
    )
    print(msg)
    raise

# Import RTL parsing helpers
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
from assertion_builder import fill_define_excel_if_needed  # type: ignore
try:
    from openpyxl import load_workbook  # type: ignore
except Exception:
    load_workbook = None  # type: ignore


def _robust_copy(src: Path, dst: Path) -> Path:
    """Copy file src->dst robustly. If dst exists or copy fails, try a unique name and raw copy."""
    target = dst
    if target.exists():
        stem = dst.stem
        suffix = dst.suffix
        for i in range(1, 1000):
            cand = dst.with_name(f"{stem}-{i}{suffix}")
            if not cand.exists():
                target = cand
                break
    try:
        shutil.copy2(src, target)
        return target
    except Exception:
        # Fallback: raw read/write
        try:
            with open(src, "rb") as rf, open(target, "wb") as wf:
                while True:
                    chunk = rf.read(1024 * 1024)
                    if not chunk:
                        break
                    wf.write(chunk)
            return target
        except Exception as e:
            raise RuntimeError(f"Copy failed: {e}")


def _create_session_excel_and_fill(state: AppState) -> Tuple[bool, str]:
    """
    Create session Excel in out/sessions/<module>-<timestamp>/, 
    verify Define sheet, run fill_define.py. Returns (ok, err).
    """
    try:
        if not state.excel_path or not Path(state.excel_path).exists():
            return False, "Reference Excel not set"
        
        # 세션 디렉터리를 out/sessions/<module>-<timestamp>/ 형태로 생성
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        mod = state.target_module or (state.module_info.module or "module")
        session_name = f"{mod}-{ts}"
        sess_dir = (_THIS_DIR.parent / "out" / "sessions" / session_name).resolve()
        sess_dir.mkdir(parents=True, exist_ok=True)
        
        # 엑셀 파일을 세션 폴더로 복사
        new_xlsx = sess_dir / f"{mod}.xlsx"
        new_xlsx = _robust_copy(Path(state.excel_path), new_xlsx)
        state.session_excel_path = new_xlsx
        
        # Verify Define sheet
        if not load_workbook:
            return False, "openpyxl missing"
        wb = load_workbook(str(new_xlsx))
        if "Define" not in wb.sheetnames:
            return False, "Define sheet missing in reference Excel"
        wb.close()
        
        # Define JSON을 같은 세션 폴더에 생성
        define_json = fill_define_excel_if_needed(new_xlsx, {
            "module": state.module_info.module,
            "clocks": state.module_info.clocks,
            "resets": state.module_info.resets,
            "inputs": state.module_info.inputs,
            "outputs": state.module_info.outputs,
            "inouts": state.module_info.inouts,
            "parameters": state.module_info.parameters,
        }, sess_dir)
        
        # Run fill_define.py
        fill_script = _THIS_DIR / "fill_define.py"
        if not fill_script.exists():
            return False, "fill_define.py not found"
        rc = subprocess.run(
            [sys.executable, str(fill_script), str(new_xlsx), str(define_json)], 
            check=False,
            capture_output=True,
            text=True
        ).returncode
        if rc != 0:
            return False, "fill_define.py failed to populate Define sheet"
        
        return True, f"Session created: {sess_dir}"
    except Exception as e:
        return False, f"Session creation error: {str(e)}"

_APP_VERSION = "v1.0"

@dataclass
class ModuleInfo:
    module: str = ""
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    inouts: List[Dict[str, Any]] = field(default_factory=list)
    clocks: List[Dict[str, Any]] = field(default_factory=list)
    resets: List[Dict[str, Any]] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AppState:
    rtl_start: Optional[Path] = None
    target_module: Optional[str] = None
    excel_path: Optional[Path] = None
    out_dir: Path = Path("out/assertions")
    modules_db: Dict[str, Any] = field(default_factory=dict)
    module_info: ModuleInfo = field(default_factory=ModuleInfo)
    occs: List[Any] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    # Session persistence id
    session_id: Optional[str] = None
    # User-defined condition signals
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    # Ports filter substring
    port_filter: Optional[str] = None
    # Onboarding wizard state
    onboarding_active: bool = False
    onboarding_stage: Optional[str] = None  # 'rtl' | 'module' | 'excel' | None
    onboarding_filter: str = ""
    onboarding_page: int = 0
    onboarding_modules: List[str] = field(default_factory=list)
    onboarding_excel_autofound: Optional[Path] = None
    onboarding_compl_index: int = 0
    onboarding_cand_page: int = 0
    onboarding_cand_visible: bool = False
    onboarding_cand_h: int = 0
    # Session Excel generated for this run
    session_excel_path: Optional[Path] = None
    excel_error: Optional[str] = None
    # Created assertions list
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    # Assertion creation wizard state
    assertion_wizard_active: bool = False
    assertion_wizard_stage: str = ""  # 'select_type' | 'input_data' | 'confirm'
    assertion_selected_type: Optional[str] = None
    assertion_input_data: Dict[str, Any] = field(default_factory=dict)

    def log(self, msg: str) -> None:
        self.messages.append(msg)
        # Limit message history
        self.messages = self.messages[-200:]


HELP_TEXT = (
    """
Type 'help' to open the full-screen overlay. Use Tab/Shift-Tab to switch pages, Esc/q to close.
"""
).strip("\n")


def _safe_str(o: Any) -> str:
    try:
        return str(o)
    except Exception:
        return repr(o)


def _get_port_width(port: Dict[str, Any]) -> str:
    """Extract bit width from port and return as string like '[7:0]' or ''."""
    width = port.get("width") or port.get("msb_lsb") or ""
    if isinstance(width, dict):
        msb = width.get('msb', '')
        lsb = width.get('lsb', '')
        if msb != '' and lsb != '':
            return f"[{msb}:{lsb}]"
    elif isinstance(width, str) and width.strip():
        return width
    return ""


def _format_port_with_width(port: Dict[str, Any], index: int) -> str:
    """Format port as '[idx] name [width]'."""
    name = port.get('name', '?')
    width = _get_port_width(port)
    if width:
        return f"[{index+1}] {name} {width}"
    return f"[{index+1}] {name}"


def _draw_ports_two_columns(win: "curses._CursesWindow", ports: List[Dict[str, Any]], start_row: int = 1) -> None:
    """Draw ports in 2-column layout with bit width information."""
    max_y, max_x = win.getmaxyx()
    usable_h = max_y - start_row - 1
    usable_w = max_x - 2
    
    # Split into two columns
    col_w = usable_w // 2
    col1_w = col_w - 1  # Space for separator
    col2_w = usable_w - col_w
    
    row = start_row
    for i in range(0, len(ports), 2):
        if row >= max_y - 1:
            break
        
        # Left column
        if i < len(ports):
            left_text = _format_port_with_width(ports[i], i)
            try:
                win.addnstr(row, 1, _truncate(left_text, col1_w), col1_w)
            except curses.error:
                pass
        
        # Right column
        if i + 1 < len(ports):
            right_text = _format_port_with_width(ports[i + 1], i + 1)
            try:
                win.addnstr(row, col_w + 1, _truncate(right_text, col2_w - 1), col2_w - 1)
            except curses.error:
                pass
        
        row += 1


def _truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "\N{HORIZONTAL ELLIPSIS}"


def build_context_from_rtl(rtl_start: Path, target_module: Optional[str]) -> Tuple[Dict[str, Any], ModuleInfo, List[Any]]:
    exts = [".v", ".sv"]
    # If a single file was provided, parse only that file; else use root + scope dir
    if rtl_start.is_file():
        files = [rtl_start]
    else:
        rtl_root, _found = find_rtl_root_from(rtl_start)
        start_scope_dir = rtl_start if rtl_start.is_dir() else rtl_start.parent
        files = sorted(set(discover_files(rtl_root, exts)) | set(discover_files(start_scope_dir, exts)), key=lambda p: str(p))
    modules = build_modules_db(files, allow_unknown=False)
    if not modules:
        raise RuntimeError("No modules parsed from RTL scope")

    if not target_module:
        tops = find_top_modules(modules)
        target_module = tops[0] if tops else next(iter(modules.keys()))

    occs = find_occurrences_of_target(modules, target_module)
    env = compute_env_for_occurrence(occs[0], modules, {}) if occs else {}
    ports_resolved = resolve_ports_with_params(modules, target_module, env)
    cls = classify_groups(modules[target_module]["ports"])
    ex_names = {x["name"] for x in cls.get("clocks", [])} | {x["name"] for x in cls.get("resets", [])}
    inputs_filtered = [it for it in ports_resolved["inputs"] if it["name"] not in ex_names]

    mi = ModuleInfo(
        module=target_module,
        inputs=inputs_filtered,
        outputs=ports_resolved["outputs"],
        inouts=ports_resolved["inouts"],
        clocks=cls.get("clocks", []),
        resets=cls.get("resets", []),
        parameters=cls.get("parameters", []),
    )
    return modules, mi, occs


def _draw_box(win: "curses._CursesWindow", title: str) -> None:
    max_y, max_x = win.getmaxyx()
    win.box()
    label = f" {title} "
    if max_x > len(label) + 2:
        try:
            win.addstr(0, 2, label, curses.A_BOLD)
        except curses.error:
            pass


def _write_lines(win: "curses._CursesWindow", lines: List[str], start_y: int = 1, start_x: int = 1) -> None:
    max_y, max_x = win.getmaxyx()
    usable_h = max_y - start_y - 1
    usable_w = max_x - start_x - 1
    row = 0
    for line in lines:
        if row >= usable_h:
            break
        try:
            win.addnstr(start_y + row, start_x, line, usable_w)
        except curses.error:
            pass
        row += 1


def _write_lines_zebra(win: "curses._CursesWindow", lines: List[str], start_y: int = 1, start_x: int = 1, base_row_index: int = 0) -> None:
    max_y, max_x = win.getmaxyx()
    usable_h = max_y - start_y - 1
    usable_w = max_x - start_x - 1
    row = 0
    for i, line in enumerate(lines):
        if row >= usable_h:
            break
        attr = curses.A_DIM if ((base_row_index + i) % 2 == 1) else 0
        try:
            win.addnstr(start_y + row, start_x, line, usable_w, attr)
        except curses.error:
            pass
        row += 1


def _write_colored_zebra(win: "curses._CursesWindow", items: List[Tuple[str, Optional[str]]], start_y: int = 1, start_x: int = 1, base_row_index: int = 0) -> None:
    max_y, max_x = win.getmaxyx()
    usable_h = max_y - start_y - 1
    usable_w = max_x - start_x - 1
    row = 0
    for i, (line, color_name) in enumerate(items):
        if row >= usable_h:
            break
        pair = curses.color_pair(_PAIR_BY_NAME.get((color_name or "").lower(), 0))
        attr = pair | (curses.A_DIM if ((base_row_index + i) % 2 == 1) else 0)
        try:
            win.addnstr(start_y + row, start_x, line, usable_w, attr)
        except curses.error:
            pass
        row += 1


def _format_kv_wrapped(items: List[Tuple[str, str]], total_width: int, label_width: int, add_blank_between: bool = True, value_color: Optional[str] = None) -> List[Tuple[str, Optional[str]]]:
    lines: List[Tuple[str, Optional[str]]] = []
    pad = " " * 2
    value_col = label_width + len(pad) + 2  # include ': '
    value_w = max(1, total_width - value_col)
    for label, value in items:
        lab = _truncate(label, label_width)
        wrapped = _textwrap(value, width=value_w) if value else [""]
        first = True
        for seg in wrapped:
            if first:
                line = f"{pad}{lab:{label_width}}: {seg}"
                first = False
            else:
                line = f"{pad}{'':{label_width}}  {seg}"
            lines.append((line, value_color))
        if add_blank_between:
            lines.append(("", None))
    return lines


def _paginate_list(items: List[str], page: int, page_size: int) -> Tuple[List[str], int]:
    if page_size <= 0:
        return items, 0
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    p = max(0, min(page, total_pages - 1))
    start = p * page_size
    end = min(len(items), start + page_size)
    return items[start:end], start


def _format_ports(title: str, ports: List[Dict[str, Any]], max_rows: int) -> List[str]:
    lines = [title]
    for idx, p in enumerate(ports[: max(0, max_rows - 1)]):
        width = p.get("width") or p.get("msb_lsb") or ""
        if isinstance(width, dict):
            width = f"[{width.get('msb', '')}:{width.get('lsb', '')}]"
        lines.append(f"  {p.get('name','?')} {width}")
    return lines


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _run_builder(state: AppState, do_fill: bool = False, do_json: bool = False, do_sv: bool = False) -> Tuple[int, str]:
    if not state.rtl_start or not state.target_module or not state.excel_path:
        return 2, "rtl/module/excel must be set first"
    _ensure_dir(state.out_dir)
    builder = _THIS_DIR / "assertion_builder.py"
    if not builder.exists():
        return 2, "scripts/assertion_builder.py not found"
    cmd = [
        sys.executable,
        str(builder),
        "--rtl-start",
        str(state.rtl_start),
        "--target-module",
        state.target_module,
        "--excel",
        str(state.excel_path),
        "--out",
        str(state.out_dir),
    ]
    if do_fill:
        cmd.append("--auto-define-fill")
    if do_json:
        cmd.append("--json")
    # run_builder always attempts to generate SV if plugins succeed; allow explicit request
    # 'do_sv' flag is informational; we still run builder regardless
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except Exception as e:  # pragma: no cover
        return 2, f"execution failed: {e}"


def _list_modules_lines(modules: Dict[str, Any], max_rows: int) -> List[str]:
    names = sorted(modules.keys())
    return ["Discovered modules:"] + [f"  {n}" for n in names[: max_rows - 1]]


def run() -> None:
    try:
        curses.wrapper(_main)
    except Exception as e:
        # Graceful fallback for rare cases where stdscr is None or curses fails
        try:
            import platform
            if platform.system() == "Windows":
                print("[Error] TUI failed to initialize (curses). If not installed, run: pip install windows-curses")
        except Exception:
            pass
        raise


def _main(stdscr: "curses._CursesWindow") -> None:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()

    state = AppState()
    state.out_dir = Path("out/assertions")

    input_buf: List[str] = []
    cursor_pos = 0
    status_msg = "Type 'help' to get started. Set paths, then 'scan'."
    last_output: List[str] = []
    # Command history
    cmd_history: List[str] = []
    hist_idx: Optional[int] = None  # None means not browsing history
    # Path completion state
    compl_items: List[Tuple[str, bool]] = []  # (name, is_dir)
    compl_base: str = ""

    # Help overlay state
    help_pages = _load_help_pages()
    overlay_active = False
    overlay_page = 0
    overlay_scroll = 0
    # Help overlay highlight term/page
    global _OVERLAY_HL_KEY, _OVERLAY_HL_TERM, _OVERLAY_PAGE_KEY, _OVERLAY_FILTER_CMD, _ERROR_MESSAGE
    _OVERLAY_HL_KEY = None
    _OVERLAY_HL_TERM = None
    _OVERLAY_PAGE_KEY = None
    _OVERLAY_FILTER_CMD = None
    _ERROR_MESSAGE = ""
    _init_color_pairs()

    # Session load and first-run flow
    sessions = _load_sessions()
    if sessions:
        chooser_result = _run_session_chooser(stdscr, sessions)
        if isinstance(chooser_result, dict):
            # Restore state from chosen session
            chosen = chooser_result
            try:
                state.rtl_start = Path(chosen.get("rtl_start", "")) if chosen.get("rtl_start") else None
            except Exception:
                state.rtl_start = None
            state.target_module = chosen.get("target_module") or None
            try:
                state.excel_path = Path(chosen.get("excel_path", "")) if chosen.get("excel_path") else None
            except Exception:
                state.excel_path = None
            try:
                if chosen.get("out_dir"):
                    state.out_dir = Path(chosen.get("out_dir")).resolve()
            except Exception:
                pass
            # Best-effort immediate scan if RTL is available
            if state.rtl_start:
                try:
                    modules, mi, occs = build_context_from_rtl(state.rtl_start, state.target_module)
                    state.modules_db = modules
                    state.module_info = mi
                    state.target_module = mi.module
                    state.occs = occs
                except Exception:
                    pass
        elif chooser_result == "new":
            state.onboarding_active = True
            state.onboarding_stage = 'rtl'
            state.onboarding_excel_autofound = _auto_find_excel()
        else:
            # quit or None → continue to normal UI
            pass
    else:
        # First run wizard instead of auto-scan
        state.onboarding_active = True
        state.onboarding_stage = 'rtl'
        state.onboarding_excel_autofound = _auto_find_excel()

    while True:
        max_y, max_x = stdscr.getmaxyx()
        stdscr.erase()

        if overlay_active:
            _render_help_overlay(stdscr, help_pages, overlay_page, overlay_scroll)
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (curses.KEY_RESIZE,):
                continue
            if ch in (27, ord('q'), ord('Q')):  # Esc or q
                overlay_active = False
                continue
            if ch in (curses.KEY_NPAGE,):
                overlay_scroll += 5
                continue
            if ch in (curses.KEY_PPAGE,):
                overlay_scroll = max(0, overlay_scroll - 5)
                continue
            # Page switch with n/N inside help
            if ch in (ord('n'),):
                overlay_page = (overlay_page + 1) % max(1, len(help_pages))
                overlay_scroll = 0
                continue
            if ch in (ord('N'),):
                overlay_page = (overlay_page - 1) % max(1, len(help_pages))
                overlay_scroll = 0
                continue
            if ch in (curses.KEY_UP,):
                overlay_scroll = max(0, overlay_scroll - 1)
                continue
            if ch in (curses.KEY_DOWN,):
                overlay_scroll += 1
                continue
            if ch in (9,):  # Tab next page
                overlay_page = (overlay_page + 1) % max(1, len(help_pages))
                overlay_scroll = 0
                continue
            if ch in (curses.KEY_BTAB,):  # Shift-Tab prev page
                overlay_page = (overlay_page - 1) % max(1, len(help_pages))
                overlay_scroll = 0
                continue
            # Any other key: ignore while overlay is open
            continue

        # Assertion wizard rendering
        if state.assertion_wizard_active:
            try:
                stdscr.erase()
            except Exception:
                pass
            _render_assertion_wizard(stdscr, state)
            max_y, max_x = stdscr.getmaxyx()
            
            # Status message
            if status_msg:
                try:
                    stdscr.addnstr(max_y - 4, 2, _truncate(status_msg, max_x - 4), max_x - 4)
                except curses.error:
                    pass
            
            # Hints
            hint_line = "Commands: set <num> <value> | done | cancel"
            try:
                stdscr.addnstr(max_y - 3, 2, _truncate(hint_line, max_x - 4), max_x - 4, curses.A_DIM)
            except curses.error:
                pass
            
            # Input prompt
            prompt = "> "
            edit_w = max_x - len(prompt) - 1
            current = "".join(input_buf)
            try:
                stdscr.addnstr(max_y - 1, 0, prompt, len(prompt))
                stdscr.addnstr(max_y - 1, len(prompt), _truncate(current, edit_w), edit_w)
                curses.curs_set(1)
                stdscr.move(max_y - 1, len(prompt) + min(cursor_pos, edit_w))
            except curses.error:
                pass
            
            stdscr.refresh()
            
            # Handle input
            ch = stdscr.getch()
            if ch in (curses.KEY_RESIZE,):
                continue
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if cursor_pos > 0:
                    del input_buf[cursor_pos - 1]
                    cursor_pos -= 1
                continue
            if ch in (curses.KEY_LEFT,):
                cursor_pos = max(0, cursor_pos - 1)
                continue
            if ch in (curses.KEY_RIGHT,):
                cursor_pos = min(len(input_buf), cursor_pos + 1)
                continue
            if ch in (10, 13):  # Enter
                cmdline = "".join(input_buf).strip()
                input_buf.clear()
                cursor_pos = 0
                if cmdline:
                    msg, exit_wizard = _handle_assertion_wizard_command(state, cmdline)
                    status_msg = msg
                    if exit_wizard:
                        state.assertion_wizard_active = False
                continue
            # Regular char
            if 0 <= ch <= 255:
                try:
                    c = chr(ch)
                except Exception:
                    c = ""
                if c:
                    input_buf.insert(cursor_pos, c)
                    cursor_pos += 1
            continue

        # Onboarding wizard rendering
        if state.onboarding_active:
            # Render onboarding UI
            # Avoid full clear here to prevent flicker of transient popups. Use erase only.
            try:
                stdscr.erase()
            except Exception:
                pass
            _render_onboarding(stdscr, state)
            max_y, max_x = stdscr.getmaxyx()
            # Optional status line for onboarding (errors/success) above candidates/hints
            if status_msg:
                try:
                    stdscr.addnstr(max_y - 5, 2, _truncate(status_msg, max_x - 4), max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
                except curses.error:
                    pass
            # Decide dynamic candidates strip height before placing hint/prompt (only in RTL step)
            # Estimate grid based on current compl_items and screen width
            cand_h = 0
            prompt_row = max_y - 2
            if (state.onboarding_stage or "") == 'rtl' and compl_items:
                try:
                    items_all = [nm + ("/" if is_dir else "") for (nm, is_dir) in compl_items]
                    longest = max((len(s) for s in items_all), default=8)
                    col_w = min(max(12, longest + 2), 32)
                    cols = max(1, (max_x - 4) // col_w)
                    rows_needed = max(1, (len(items_all) + cols - 1) // cols)
                    # Header + rows, limit to 10 and to available space
                    cand_h = min(10, rows_needed + 1, max(0, max_y - 4))
                    cand_h = max(3, cand_h)
                    state.onboarding_cand_h = cand_h
                    state.onboarding_cand_visible = True
                except Exception:
                    cand_h = 3
                    state.onboarding_cand_h = cand_h
                    state.onboarding_cand_visible = True
            # Anchor candidates to the line just above the prompt; grow upwards
            if cand_h:
                cand_bottom = prompt_row - 1
                cand_top = max(1, cand_bottom - (cand_h - 1))
                hint_y = max(1, cand_top - 1)
            else:
                cand_top = 0
                hint_y = prompt_row - 1
            try:
                stdscr.move(hint_y, 0)
                stdscr.clrtoeol()
                stage = (state.onboarding_stage or "").lower()
                if stage == 'rtl':
                    hint_text = "Enter path and press Enter. Tab: complete. Esc: cancel."
                elif stage == 'module':
                    hint_text = "Type number. f <text>: filter, F: clear, n/N: page, prev/back: previous"
                else:
                    hint_text = "Type path and Enter (or accept autodetected). prev/back: previous"
                stdscr.addnstr(hint_y, 2, _truncate(hint_text, max_x - 4), max_x - 4, curses.A_DIM)
            except curses.error:
                pass

            # (popup rendered after prompt, just before blocking getch)
            # Input prompt (force clear to prevent ghosting) placed near bottom
            prompt = "> "
            edit_w = max_x - len(prompt) - 1
            current = "".join(input_buf)
            try:
                stdscr.addnstr(max_y - 2, 0, " " * max_x, max_x)
                stdscr.addstr(max_y - 2, 0, prompt)
                stdscr.addnstr(max_y - 2, len(prompt), _truncate(current, edit_w), edit_w)
                try:
                    curses.curs_set(1)
                except Exception:
                    pass
                stdscr.move(max_y - 2, len(prompt) + min(cursor_pos, edit_w))
            except curses.error:
                pass
            # Draw candidates strip last on stdscr (wide, up to 10 lines) so it persists reliably and doesn't overlap (RTL step only)
            if (state.onboarding_stage or "") == 'rtl' and compl_items and cand_h:
                try:
                    # Recompute anchored top using prompt row and current cand_h so it won't drift
                    prompt_row = max_y - 2
                    cand_bottom = prompt_row - 1
                    cand_top = max(1, cand_bottom - (cand_h - 1))
                    # Clear the region
                    for r in range(cand_h):
                        stdscr.move(cand_top + r, 0); stdscr.clrtoeol()
                    items_all = [nm + ("/" if is_dir else "") for (nm, is_dir) in compl_items]
                    # Header on first line
                    stdscr.addnstr(cand_top, 2, _truncate("Candidates:", max_x - 4), max_x - 4, curses.A_BOLD)
                    # Grid layout for alignment
                    grid_rows = max(1, cand_h - 1)
                    # Determine column width from longest label, clamp for readability
                    longest = max((len(s) for s in items_all), default=8)
                    col_w = min(max(12, longest + 2), 32)
                    cols = max(1, (max_x - 4) // col_w)
                    visible_capacity = grid_rows * cols
                    # Paging
                    total_pages = max(1, (len(items_all) + visible_capacity - 1) // visible_capacity)
                    cur_page = state.onboarding_cand_page % total_pages
                    start_idx = cur_page * visible_capacity
                    items = items_all[start_idx:start_idx + visible_capacity]
                    for r in range(grid_rows):
                        for c in range(cols):
                            idx = r * cols + c
                            if idx >= len(items):
                                break
                            label = items[idx]
                            x = 2 + c * col_w
                            y = cand_top + 1 + r
                            stdscr.addnstr(y, x, _truncate(label, col_w - 1), col_w - 1, curses.color_pair(_PAIR_BY_NAME.get("cyan",0)))
                    # If truncated, show (more)
                    if total_pages > 1:
                        more_text = f"... (more {cur_page+1}/{total_pages})"
                        stdscr.addnstr(cand_top + grid_rows, max(2, max_x - len(more_text) - 2), _truncate(more_text, len(more_text)), len(more_text), curses.A_DIM)
                except curses.error:
                    pass
            stdscr.refresh()
            ch = stdscr.getch()
            # Basic editing keys
            if ch in (curses.KEY_RESIZE,):
                continue
            if ch in (27,):  # Esc cancels onboarding
                state.onboarding_active = False
                state.onboarding_stage = None
                input_buf.clear(); cursor_pos = 0
                continue
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if cursor_pos > 0:
                    del input_buf[cursor_pos - 1]
                    cursor_pos -= 1
                continue
            if ch in (curses.KEY_DC,):
                if cursor_pos < len(input_buf):
                    del input_buf[cursor_pos]
                continue
            if ch in (curses.KEY_LEFT,):
                cursor_pos = max(0, cursor_pos - 1); continue
            if ch in (curses.KEY_RIGHT,):
                cursor_pos = min(len(input_buf), cursor_pos + 1); continue
            if ch in (curses.KEY_HOME,):
                cursor_pos = 0; continue
            if ch in (curses.KEY_END,):
                cursor_pos = len(input_buf); continue
            # Tab completion for path (raw mode in onboarding): Linux-like
            if ch == 9:
                line = "".join(input_buf)
                # In onboarding, treat whole line as path prefix
                new_line, new_cursor, items, base_dir = _path_complete_raw(line, cursor_pos)
                if items:
                    # Show candidates; insert ONLY common prefix increment (no first-item commit)
                    compl_base = base_dir
                    compl_items = items
                    names = [nm for (nm, _isdir) in items]
                    common = _common_prefix(names)
                    base_str = str(base_dir).rstrip("/\\").replace("\\", "/")
                    next_prefix = (base_str + "/" + common) if base_str else common
                    # If common grows beyond current typed prefix, extend input by the new delta only
                    if next_prefix and not line.endswith(next_prefix):
                        input_buf = list(next_prefix)
                        cursor_pos = len(input_buf)
                        # typing happened implicitly → ensure candidate page stays at 0 on first Tab
                        if not state.onboarding_cand_visible:
                            state.onboarding_cand_page = 0
                        state.onboarding_cand_visible = True
                    else:
                        # No new common part → advance candidates page (wrap)
                        # Compute paging using same geometry as renderer
                        max_y, max_x = stdscr.getmaxyx()
                        # Recompute dynamic grid
                        longest = max((len(nm + ('/' if isd else '')) for (nm, isd) in items), default=8)
                        col_w = min(max(12, longest + 2), 32)
                        cols = max(1, (max_x - 4) // col_w)
                        # Use last computed cand_h from state to keep baseline anchored
                        grid_rows = max(1, (state.onboarding_cand_h - 1) if state.onboarding_cand_h else 6)
                        visible_capacity = grid_rows * cols
                        total_pages = max(1, (len(items) + visible_capacity - 1) // visible_capacity)
                        state.onboarding_cand_page = (state.onboarding_cand_page + 1) % total_pages
                else:
                    # No candidates: apply common-prefix if any; otherwise do nothing (beep)
                    if new_line != line:
                        input_buf = list(new_line)
                        cursor_pos = new_cursor
                    else:
                        try:
                            curses.beep()
                        except Exception:
                            pass
                continue
            # Enter: commit
            if ch in (10, 13, curses.KEY_ENTER):
                cmdline = "".join(input_buf).strip()
                stage = state.onboarding_stage or ""
                # Default: clear status unless error occurs
                status_msg = ""
                if stage == 'rtl':
                    from pathlib import Path as _P
                    p = _P(cmdline).expanduser()
                    if str(p).strip() and p.exists():
                        state.rtl_start = p
                        # Build modules list for next step
                        try:
                            mods_ctx, _mi, _occs = build_context_from_rtl(p, None)
                            state.onboarding_modules = sorted(list(mods_ctx.keys()))
                        except Exception:
                            state.onboarding_modules = []
                        state.onboarding_stage = 'module'
                        # Hard clear once when moving to Step 2 to avoid residuals
                        try:
                            # Use the current stdscr provided to _main via closure; avoid global curses.stdscr
                            stdscr.clear(); stdscr.refresh()
                        except Exception:
                            pass
                        status_msg = f"rtl set: {p}"
                        input_buf.clear(); cursor_pos = 0
                    else:
                        status_msg = "Invalid RTL path (not found)."
                        # keep input so user can edit
                elif stage == 'excel':
                    # Delegate to command handler (supports empty accept)
                    out_msg, opened_overlay = _handle_command(state, cmdline)
                    input_buf.clear(); cursor_pos = 0
                    if opened_overlay:
                        overlay_active = True
                        overlay_page = 0
                        overlay_scroll = 0
                    else:
                        status_msg = out_msg or status_msg
                else:
                    # For 'module' and any other, delegate to handler
                    out_msg, opened_overlay = _handle_command(state, cmdline)
                    input_buf.clear(); cursor_pos = 0
                    if opened_overlay:
                        overlay_active = True
                        overlay_page = 0
                        overlay_scroll = 0
                    else:
                        status_msg = out_msg or status_msg
                continue
            # Regular char (any typing clears candidates)
            if 0 <= ch <= 255:
                try:
                    c = chr(ch)
                except Exception:
                    c = ""
                if c:
                    input_buf.insert(cursor_pos, c)
                    cursor_pos += 1
                    compl_items = []
            continue

        # Normal dashboard rendering
        # 레이아웃 구조:
        # - Left: Module/Paths (top) + Clocks/Resets/Params (bottom) - 20% width, full height
        # - Right (80%): 상단 60% - Inputs | Outputs | Condition Signals (3등분)
        #                하단 40% - Created Assertions (전체 너비)
        
        left_w = max(24, int(max_x * 0.20))  # Fixed 20% for left panel
        right_w = max_x - left_w  # 80% for right side
        
        # Right side 상단 60%, 하단 40%
        right_top_h = max(6, int((max_y - 3) * 0.60))  # -3 for prompt area
        right_bottom_h = max(6, max_y - 3 - right_top_h)
        
        # Right top area split into 3 equal columns: Inputs | Outputs | Condition Signals
        col_w = right_w // 3
        in_w = col_w
        out_w = col_w
        cond_w = right_w - in_w - out_w  # Remaining width
        
        # Create windows
        # Left side: Module/Paths (top) + Clocks/Resets/Params (bottom)
        left_top_h = max(7, min(14, right_top_h // 2))
        left_bot_h = max(3, max_y - 3 - left_top_h)  # Extend to bottom
        
        win_left_top = curses.newwin(left_top_h, left_w, 0, 0)
        win_left_bot = curses.newwin(left_bot_h, left_w, left_top_h, 0)
        
        # Right top: Inputs | Outputs | Condition Signals
        win_in = curses.newwin(right_top_h, in_w, 0, left_w)
        win_out = curses.newwin(right_top_h, out_w, 0, left_w + in_w)
        win_cond = curses.newwin(right_top_h, cond_w, 0, left_w + in_w + out_w)
        
        # Right bottom: Created Assertions (spans full right width)
        win_assertions = curses.newwin(right_bottom_h, right_w, right_top_h, left_w)

        # Draw left-top: Module/IP info (two-column KV with wrapping and zebra)
        _draw_box(win_left_top, "Module / Paths")
        excel_show = state.session_excel_path or state.excel_path or ""
        kv_items = [
            ("RTL", _safe_str(state.rtl_start or "")),
            ("Module", state.module_info.module or (state.target_module or "")),
            ("Excel", _safe_str(excel_show)),
            ("Out", _safe_str(state.out_dir)),
        ]
        inner_w = left_w - 2
        max_label = max(len(k) for k, _ in kv_items) if kv_items else 8
        label_w = min(max(8, max_label), max(8, inner_w // 3))
        # Try to auto-detect Excel path if missing
        excel_color: Optional[str] = None
        if not state.excel_path:
            auto_excel = _auto_find_excel()
            if auto_excel:
                state.excel_path = auto_excel
            else:
                excel_color = "red"
        # Color Excel line red if an Excel error occurred
        value_color = None
        kv_tuples = _format_kv_wrapped(kv_items, total_width=inner_w, label_width=label_w, add_blank_between=True, value_color=value_color)
        # Re-color Excel line to red if missing
        recolored: List[Tuple[str, Optional[str]]] = []
        for line, color in kv_tuples:
            if line.strip().startswith("Excel") and (excel_color or state.excel_error):
                recolored.append((line, "red"))
            else:
                recolored.append((line, color))
        # Write KV section
        row_ptr_left = 1
        _write_colored_zebra(win_left_top, recolored, row_ptr_left, 1, base_row_index=0)
        # Show short error under Excel if any
        if state.excel_error:
            try:
                win_left_top.addnstr(row_ptr_left + len(recolored), 1, _truncate(f"Excel error: {_safe_str(state.excel_error)}", inner_w - 2), inner_w - 2, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw left-bottom: clocks/resets/params with numbering for clocks/resets
        _draw_box(win_left_bot, "Clocks / Resets / Params")
        left_bot_h, left_bot_w = win_left_bot.getmaxyx()
        row_ptr_left_bot = 1  # Start from row 1
        sections = [
            ("Clocks:", [f"  [{i+1}] {c.get('name','?')}" for i, c in enumerate(state.module_info.clocks)]),
            ("Resets:", [f"  [{i+1}] {r.get('name','?')}" for i, r in enumerate(state.module_info.resets)]),
            ("Params:", [f"  {p.get('name','?')}" for p in state.module_info.parameters]),
        ]
        for title, items in sections:
            if row_ptr_left_bot >= left_bot_h - 1:
                break
            lines = [title] + items + [""]
            _write_lines_zebra(win_left_bot, lines, row_ptr_left_bot, 1, base_row_index=0)
            row_ptr_left_bot += len(lines)

        # Draw Inputs and Outputs columns with 2-column layout, numbering, and bit width
        _draw_box(win_in, "Inputs")
        _draw_box(win_out, "Outputs")
        
        # Apply port filter if set
        def _apply_filter(pl: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            if not state.port_filter:
                return pl
            key = state.port_filter.lower()
            return [p for p in pl if key in (p.get('name','').lower())]
        
        # Include inouts into both lists if any
        in_ports = _apply_filter(state.module_info.inputs + state.module_info.inouts)
        out_ports = _apply_filter(state.module_info.outputs + state.module_info.inouts)
        
        # Pagination support (global _ports_page)
        global _ports_page
        try:
            _ports_page
        except NameError:
            _ports_page = 0
        
        in_h, in_w2 = win_in.getmaxyx()
        out_h, out_w2 = win_out.getmaxyx()
        avail_rows_in = in_h - 2
        avail_rows_out = out_h - 2
        
        # Calculate how many ports fit per page (2 columns)
        ports_per_page_in = avail_rows_in * 2
        ports_per_page_out = avail_rows_out * 2
        
        # Paginate
        in_start = _ports_page * ports_per_page_in
        out_start = _ports_page * ports_per_page_out
        in_page_ports = in_ports[in_start:in_start + ports_per_page_in]
        out_page_ports = out_ports[out_start:out_start + ports_per_page_out]
        
        # Draw in 2-column layout
        _draw_ports_two_columns(win_in, in_page_ports, start_row=1)
        _draw_ports_two_columns(win_out, out_page_ports, start_row=1)
        
        # Draw rightmost: Condition Signals as 2-column KV (name | expr)
        _draw_box(win_cond, "Condition Signals (ms)")
        cond_h, cond_w2 = win_cond.getmaxyx()
        cond_inner_w = cond_w2 - 2
        
        def _label_with_bits(c: Dict[str, Any]) -> Tuple[str, str]:
            nm = c.get('name', '')
            bits = c.get('bits', 1)
            label = f"{nm} ({bits}bits)" if bits and bits > 1 else nm
            return label, c.get('expr', '')
        
        cond_items = [_label_with_bits(c) for c in state.conditions]
        max_name = max((len(nm) for nm, _ in cond_items), default=8)
        name_w = min(max(8, max_name), max(8, cond_inner_w // 3))
        cond_lines = _format_kv_wrapped(cond_items, total_width=cond_inner_w, label_width=name_w, add_blank_between=True, value_color=None)
        _write_colored_zebra(win_cond, cond_lines, 1, 1, base_row_index=0)

        # Draw bottom: Assertion List (spans full width)
        _draw_box(win_assertions, "Created Assertions")
        assert_h, assert_w = win_assertions.getmaxyx()
        assert_inner_h = assert_h - 2
        assert_inner_w = assert_w - 2
        
        if not state.assertions:
            no_assert_msg = "No assertions created yet. Use 'new' command to create assertions."
            try:
                win_assertions.addnstr(1, 2, _truncate(no_assert_msg, assert_inner_w), assert_inner_w, curses.A_DIM)
            except curses.error:
                pass
        else:
            # Display assertions in table format: Type | Signals | Description
            # Column widths: Type(15%) | Signals(35%) | Description(50%)
            type_w = max(10, int(assert_inner_w * 0.15))
            sig_w = max(15, int(assert_inner_w * 0.35))
            desc_w = max(20, assert_inner_w - type_w - sig_w - 4)  # -4 for separators
            
            # Header
            header = f"{'Type':<{type_w}} | {'Signals':<{sig_w}} | {'Description':<{desc_w}}"
            try:
                win_assertions.addnstr(1, 2, _truncate(header, assert_inner_w), assert_inner_w, curses.A_BOLD)
            except curses.error:
                pass
            
            # Separator
            sep = "-" * (type_w + sig_w + desc_w + 4)
            try:
                win_assertions.addnstr(2, 2, _truncate(sep, assert_inner_w), assert_inner_w)
            except curses.error:
                pass
            
            # Assertion rows
            row = 3
            for i, asrt in enumerate(state.assertions):
                if row >= assert_h - 1:
                    break
                atype = asrt.get('type', 'Unknown')
                signals = asrt.get('signals', [])
                sig_str = ', '.join(signals[:3]) + ('...' if len(signals) > 3 else '')
                desc = asrt.get('description', '')
                
                line = f"{_truncate(atype, type_w):<{type_w}} | {_truncate(sig_str, sig_w):<{sig_w}} | {_truncate(desc, desc_w):<{desc_w}}"
                attr = curses.A_DIM if (i % 2 == 1) else 0
                try:
                    win_assertions.addnstr(row, 2, _truncate(line, assert_inner_w), assert_inner_w, attr)
                except curses.error:
                    pass
                row += 1

        # Completion popup above status/hints if available
        comp_win = None
        if compl_items:
            comp_h = min(len(compl_items) + 2, 10)
            comp_y = max_y - 3 - comp_h
            if comp_y >= 0:
                comp_win = curses.newwin(comp_h, max_x, comp_y, 0)
                comp_win.box()
                title = f" {compl_base} "
                try:
                    comp_win.addnstr(0, 2, _truncate(title, max_x - 4), max_x - 4, curses.A_BOLD)
                except curses.error:
                    pass
                for i, (name, is_dir) in enumerate(compl_items[: comp_h - 2]):
                    color = _PAIR_BY_NAME.get("cyan", 0) if not is_dir else 0
                    attr = curses.color_pair(color)
                    label = name + ("/" if is_dir else "")
                    try:
                        comp_win.addnstr(1 + i, 2, _truncate(label, max_x - 4), max_x - 4, attr)
                    except curses.error:
                        pass
                comp_win.refresh()

        # Status/messages just above the command hints (or below completion)
        status_y = max_y - 3
        try:
            stdscr.addnstr(status_y, 0, _truncate(status_msg, max_x - 1), max_x - 1, curses.A_REVERSE)
        except curses.error:
            pass

        # Command hints line (second last line)
        hints = "[help] [new] [scan] [set rtl|module|excel|out] [fill] [json] [sv] [ms] [f/F] [n/N] [quit|q]"
        try:
            stdscr.addnstr(max_y - 2, 0, _truncate(hints, max_x - 1), max_x - 1)
        except curses.error:
            pass

        # Input prompt (last line)
        prompt = "> "
        edit_w = max_x - len(prompt) - 1
        current = "".join(input_buf)
        vis = current
        try:
            stdscr.addnstr(max_y - 1, 0, prompt, len(prompt))
            stdscr.addnstr(max_y - 1, len(prompt), _truncate(vis, edit_w), edit_w)
            # Show cursor position if inside visible region
            curses.curs_set(1)
            stdscr.move(max_y - 1, len(prompt) + min(cursor_pos, edit_w))
        except curses.error:
            pass

        stdscr.refresh()
        win_left_top.refresh()
        win_left_bot.refresh()
        win_in.refresh()
        win_out.refresh()
        win_cond.refresh()
        win_assertions.refresh()

        ch = stdscr.getch()
        if ch in (curses.KEY_RESIZE,):
            continue
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if cursor_pos > 0:
                del input_buf[cursor_pos - 1]
                cursor_pos -= 1
            continue
        if ch in (curses.KEY_LEFT,):
            cursor_pos = max(0, cursor_pos - 1)
            continue
        if ch in (curses.KEY_RIGHT,):
            cursor_pos = min(len(input_buf), cursor_pos + 1)
            continue
        # History navigation
        if ch in (curses.KEY_UP,):
            if cmd_history:
                if hist_idx is None:
                    hist_idx = len(cmd_history) - 1
                else:
                    hist_idx = max(0, hist_idx - 1)
                recalled = cmd_history[hist_idx]
                input_buf = list(recalled)
                cursor_pos = len(input_buf)
            continue
        if ch in (curses.KEY_DOWN,):
            if cmd_history and hist_idx is not None:
                if hist_idx < len(cmd_history) - 1:
                    hist_idx += 1
                    recalled = cmd_history[hist_idx]
                    input_buf = list(recalled)
                    cursor_pos = len(input_buf)
                else:
                    hist_idx = None
                    input_buf = []
                    cursor_pos = 0
            continue
        # Removed Ctrl+N/Ctrl+P paging (now handled by 'n'/'N' commands)
        # Tab path completion
        if ch == 9:
            line = "".join(input_buf)
            new_line, new_cursor, items, base_dir = _path_complete(line, cursor_pos)
            input_buf = list(new_line)
            cursor_pos = new_cursor
            compl_items = items
            compl_base = base_dir
            continue
        if ch in (curses.KEY_HOME,):
            cursor_pos = 0
            continue
        if ch in (curses.KEY_END,):
            cursor_pos = len(input_buf)
            continue
        if ch in (curses.KEY_DC,):  # Delete key
            if cursor_pos < len(input_buf):
                del input_buf[cursor_pos]
            continue
        if ch in (10, 13):  # Enter
            cmdline = "".join(input_buf).strip()
            input_buf.clear()
            cursor_pos = 0
            compl_items = []  # clear completion popup
            if not cmdline:
                status_msg = ""
                continue
            status_msg = f"$ {cmdline}"
            # push history
            if not (cmd_history and cmd_history[-1] == cmdline):
                cmd_history.append(cmdline)
            hist_idx = None
            out_msg, opened_overlay = _handle_command(state, cmdline)
            if opened_overlay:
                overlay_active = True
                # If a target page was requested, honor it
                if _OVERLAY_PAGE_KEY:
                    idx = _find_help_page_index(help_pages, _OVERLAY_PAGE_KEY)
                    overlay_page = max(0, idx)
                else:
                    overlay_page = 0
                overlay_scroll = 0
            last_output = out_msg.splitlines() if out_msg else []
            continue
        if 0 <= ch <= 255:
            try:
                c = chr(ch)
            except Exception:
                c = ""
            if c:
                input_buf.insert(cursor_pos, c)
                cursor_pos += 1
                compl_items = []  # typing clears completion


def _handle_command(state: AppState, cmdline: str) -> Tuple[str, bool]:
    # Onboarding: allow empty input for Excel stage to accept auto-detected file
    if state.onboarding_active and (state.onboarding_stage or "") == 'excel':
        if (cmdline.strip() == "") and state.onboarding_excel_autofound and not state.excel_path:
            state.excel_path = state.onboarding_excel_autofound
            state.onboarding_active = False
            state.onboarding_stage = None
            _save_session_snapshot(state)
            return f"Excel set: {state.excel_path}", False
    toks = cmdline.split()
    if not toks:
        return "", False
    raw_cmd = toks[0]
    cmd = raw_cmd.lower()
    args = toks[1:]

    # Onboarding-friendly shortcuts
    if state.onboarding_active:
        stage = state.onboarding_stage or ""
        # 1) RTL stage: accept raw path without 'set rtl'
        if stage == 'rtl':
            from pathlib import Path as _P
            try:
                p = _P(cmdline).expanduser()
                if str(p).strip() and p.exists():
                    state.rtl_start = p
                    # Build modules list for next stage
                    try:
                        mods_ctx, _mi, _occs = build_context_from_rtl(p, None)
                        # If file: only modules from that file
                        if p.is_file():
                            from rtl_parser import modules_defined_under  # type: ignore
                            # Use helper to filter modules by file path
                            cand = [name for name, m in mods_ctx.items() if Path(m["file"]).resolve() == p.resolve()]
                            state.onboarding_modules = sorted(list(set(cand)))
                        else:
                            state.onboarding_modules = sorted(list(mods_ctx.keys()))
                    except Exception:
                        state.onboarding_modules = []
                    state.onboarding_stage = 'module'
                    return f"rtl set: {p}", False
            except Exception:
                pass
        # 2) Module stage: number to pick, f filter, F clear, n/N page (wrap), prev/back to return
        if stage == 'module':
            if cmdline.isdigit():
                idx = int(cmdline) - 1
                if 0 <= idx < len(state.onboarding_modules):
                    state.target_module = state.onboarding_modules[idx]
                    # If starting scope was a directory, bind rtl_start to chosen module's file
                    try:
                        if state.modules_db and state.target_module in state.modules_db:
                            fpath = Path(state.modules_db[state.target_module]["file"])  # type: ignore
                            if fpath.exists():
                                state.rtl_start = fpath
                        # Refresh module_info now so panels have data in Step 3
                        modules, mi, occs = build_context_from_rtl(state.rtl_start or Path("."), state.target_module)
                        state.modules_db = modules
                        state.module_info = mi
                        state.occs = occs
                    except Exception:
                        pass
                    state.onboarding_stage = 'excel'
                    return f"Picked module: {state.target_module}", False
            if cmd == 'f' and args:
                state.onboarding_filter = " ".join(args)
                state.onboarding_page = 0
                return f"Filter set: {state.onboarding_filter}", False
            if raw_cmd == 'F' or (cmd == 'f' and not args):
                state.onboarding_filter = ""
                state.onboarding_page = 0
                return "Filter cleared", False
            if cmd == 'n' and not args:
                # wrap around
                total = len(state.onboarding_modules)
                page_size = max(1, (8 if True else 8))  # placeholder, will be recomputed in render
                pages = max(1, (total + page_size - 1) // page_size)
                state.onboarding_page = (state.onboarding_page + 1) % pages
                return f"Page {state.onboarding_page}", False
            if raw_cmd == 'N' and not args:
                total = len(state.onboarding_modules)
                page_size = max(1, (8 if True else 8))
                pages = max(1, (total + page_size - 1) // page_size)
                state.onboarding_page = (state.onboarding_page - 1) % pages
                return f"Page {state.onboarding_page}", False
            if cmd in ("prev", "back"):
                state.onboarding_stage = 'rtl'
                return "Back to Step 1/3 — RTL", False
        # 3) Excel stage: accept empty to take autodetected; or raw path
        if stage == 'excel':
            from pathlib import Path as _P
            if not cmdline and state.onboarding_excel_autofound:
                state.excel_path = state.onboarding_excel_autofound
                state.onboarding_active = False
                state.onboarding_stage = None
                _save_session_snapshot(state)
                # Create per-session Excel and prefill Define
                ok, err = _create_session_excel_and_fill(state)
                if not ok:
                    state.excel_error = err or "Excel error"
                    _set_error_message(state.excel_error)
                return f"Excel set: {state.excel_path}", False
            try:
                p = _P(cmdline).expanduser()
                if str(p).strip() and p.exists():
                    state.excel_path = p
                    state.onboarding_active = False
                    state.onboarding_stage = None
                    _save_session_snapshot(state)
                    ok, err = _create_session_excel_and_fill(state)
                    if not ok:
                        state.excel_error = err or "Excel error"
                        _set_error_message(state.excel_error)
                    return f"Excel set: {state.excel_path}", False
                if cmd in ("prev", "back"):
                    state.onboarding_stage = 'module'
                    return "Back to Step 2/3 — Module", False
            except Exception:
                pass

    if cmd in ("help", "h"):
        return "Showing help...", True
    
    if cmd == "new":
        # Enter assertion creation wizard
        if not state.module_info.module:
            return "Please scan RTL first (use 'scan' command)", False
        
        # Create session Excel if not already created
        if not state.session_excel_path:
            if not state.excel_path or not Path(state.excel_path).exists():
                return "Reference Excel not set. Please set Excel path first.", False
            
            ok, err = _create_session_excel_and_fill(state)
            if not ok:
                return f"Failed to create session Excel: {err}", False
        
        state.assertion_wizard_active = True
        state.assertion_wizard_stage = 'select_type'
        state.assertion_selected_type = None
        state.assertion_input_data.clear()
        return "Entering assertion creator wizard...", False
    
    if cmd in ("n", "N") and not args:
        # Port paging via command
        global _ports_page
        try:
            _ports_page
        except NameError:
            _ports_page = 0
        if raw_cmd == "N":
            _ports_page = max(0, _ports_page - 1)
        else:
            _ports_page += 1
        return f"Ports page: {_ports_page}", False

    if cmd in ("quit", "q", "exit"):
        raise SystemExit(0)
    if cmd == "clear":
        state.messages.clear()
        return "Cleared messages", False

    if cmd == "set" and args:
        if args[0] == "rtl" and len(args) >= 2:
            p = Path(" ".join(args[1:])).expanduser().resolve()
            state.rtl_start = p
            return f"rtl set: {p}", False
        if args[0] == "module" and len(args) >= 2:
            state.target_module = " ".join(args[1:])
            return f"module set: {state.target_module}", False
        if args[0] == "excel" and len(args) >= 2:
            p = Path(" ".join(args[1:])).expanduser().resolve()
            state.excel_path = p
            return f"excel set: {p}", False
        if args[0] == "out" and len(args) >= 2:
            p = Path(" ".join(args[1:])).expanduser().resolve()
            state.out_dir = p
            return f"out set: {p}", False
        return "Usage: set rtl|module|excel|out <value>", False

    if cmd == "scan":
        if not state.rtl_start:
            return "Set rtl first: set rtl <path>", False
        try:
            modules, mi, occs = build_context_from_rtl(state.rtl_start, state.target_module)
            state.modules_db = modules
            state.module_info = mi
            state.target_module = mi.module
            state.occs = occs
            tops = find_top_modules(modules)
            extra = f" (tops: {', '.join(tops[:5])}{'...' if len(tops)>5 else ''})" if tops else ""
            return f"Scan complete. Target: {mi.module}{extra}", False
        except Exception as e:
            return f"Scan failed: {e}", False

    if cmd == "list" and args and args[0] == "modules":
        if not state.modules_db:
            return "No modules. Run scan first.", False
        names = sorted(state.modules_db.keys())
        preview = "\n".join(["Discovered modules:"] + names[:100])
        more = " (truncated)" if len(names) > 100 else ""
        return preview + more, False

    if cmd == "pick" and args:
        name = " ".join(args)
        if state.modules_db and name in state.modules_db:
            state.target_module = name
            # Recompute module_info for the new pick
            try:
                _, mi, occs = build_context_from_rtl(state.rtl_start or Path("."), state.target_module)
                state.module_info = mi
                state.occs = occs
            except Exception:
                pass
            # Persist session
            _save_session_snapshot(state)
            return f"Picked: {name}", False
        return f"Module not found: {name}", False

    if cmd in ("fill", "json", "sv"):
        do_fill = cmd == "fill"
        do_json = cmd == "json"
        do_sv = cmd == "sv"
        rc, out = _run_builder(state, do_fill=do_fill, do_json=do_json, do_sv=do_sv)
        _save_session_snapshot(state)
        return (("OK" if rc == 0 else f"RC={rc}") + "\n" + (out or "")), False

    if cmd == "ms":
        # Syntax: ms <name> = <expr>
        rest = " ".join(args).strip()
        if not rest or "=" not in rest:
            # support 'ms name expr' (no '=')
            parts = rest.split()
            if len(parts) >= 2:
                name = parts[0]
                expr = " ".join(parts[1:])
            else:
                _highlight_ms_help()
                _set_help_filter_cmd("ms")
                _set_error_message("Invalid input: usage ms <name> = <expr> or ms <name> <expr>")
                return "Invalid input. See ms help.", True
        else:
            name, expr = rest.split("=", 1)
        name = name.strip()
        expr = expr.strip()
        # Extract trailing width token if present (e.g., '... 4')
        trailing_width: Optional[int] = None
        try:
            toks = expr.split()
            if toks and toks[-1].isdigit():
                trailing_width = int(toks[-1])
                expr = " ".join(toks[:-1]).strip()
        except Exception:
            pass
        # Map numeric aliases 1.. to input/inout, oN to outputs
        def _alias_replace(token: str) -> str:
            if token.startswith('o') and token[1:].isdigit():
                idx = int(token[1:])
                outs = (state.module_info.outputs + state.module_info.inouts)
                if 1 <= idx <= len(outs):
                    return outs[idx-1].get('name','')
            if token.isdigit():
                ins = (state.module_info.inputs + state.module_info.inouts)
                idx = int(token)
                if 1 <= idx <= len(ins):
                    return ins[idx-1].get('name','')
            return token
        expr_tokens = _tokenize_expr(expr)
        expr_tokens = [ _alias_replace(t) for t in expr_tokens ]
        expr = " ".join(expr_tokens)
        if not name or not expr:
            _highlight_ms_help()
            _set_help_filter_cmd("ms")
            _set_error_message("Invalid input: name/expr missing")
            return "Invalid input. See ms help.", True
        ok, err = _validate_condition_expr(expr, state)
        if not ok:
            _highlight_ms_help()
            _set_help_filter_cmd("ms")
            _set_error_message(f"Invalid signal expression: {err}")
            return f"Invalid signal expression: {err}", True
        # Cycle detection
        try:
            if _has_cycle_with_new(name, expr, state):
                _highlight_ms_help()
                _set_help_filter_cmd("ms")
                _set_error_message("Cycle detected among condition signals")
                return "Invalid: cycle detected", True
        except Exception:
            pass
        # Infer width from selects if present; fallback to trailing_width or 1
        width = trailing_width or 1
        # Simple inference: detect [msb:lsb]
        import re
        m = re.search(r"\[(\d+)\s*:\s*(\d+)\]", expr)
        if m:
            try:
                msb = int(m.group(1)); lsb = int(m.group(2))
                if msb >= lsb:
                    width = (msb - lsb + 1)
                    _set_error_message(f"Note: bit-select interpreted as {width} bits")
            except Exception:
                pass
        # Store and refresh UI (show as name (Nbits))
        state.conditions.append({"name": name, "expr": expr, "bits": width})
        _save_session_snapshot(state)
        # Append to session Excel Define sheet starting at L8 if available
        try:
            if state.session_excel_path and load_workbook:
                wb = load_workbook(str(state.session_excel_path))
                ws = wb[wb.sheetnames[0]]  # assume first sheet is Define or compatible
                # Find first empty row from 8 downward in column L
                r = 8
                while ws.cell(row=r, column=12).value not in (None, ""):
                    r += 1
                ws.cell(row=r, column=12, value=name)
                ws.cell(row=r, column=13, value=expr)
                ws.cell(row=r, column=14, value=width)
                wb.save(str(state.session_excel_path))
        except Exception as e:
            _set_error_message(f"Excel append failed: {e}")
        _save_session_snapshot(state)
        return f"Condition added: {name} ({width}bits)", False

    if cmd == "f" or raw_cmd == "F":
        # f <substr> to set filter; F (upper) or 'f' without args to clear
        if cmd == "f" and args:
            state.port_filter = " ".join(args).strip()
            return f"Filter set: {state.port_filter}", False
        state.port_filter = None
        return "Filter cleared", False

    return f"Unknown command: {cmd} (try 'help')", False


# ---------------------------- HELP OVERLAY ---------------------------------

def _load_help_pages() -> List[Dict[str, Any]]:
    cfg_path = _THIS_DIR / "help_config.json"
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        pages = raw.get("pages", [])
        if isinstance(pages, list):
            return pages
    except Exception:
        pass
    # Fallback minimal page
    return [
        {
            "key": "fallback",
            "title": "Help",
            "items": [
                {"text": "help | h            Open/close this overlay", "color": "white"},
                {"text": "scan                Parse RTL and populate panels", "color": "cyan"},
                {"text": "set rtl <path>      Set RTL path (Tab: path complete)", "color": "green"},
                {"text": "set module <name>   Set target module", "color": "green"},
                {"text": "set excel <path>    Set Excel path (auto-detected if possible)", "color": "green"},
                {"text": "set out <path>      Set output directory", "color": "green"},
                {"text": "fill | json | sv    Generate Define/JSON/SV", "color": "yellow"},
                {"text": "f <substr> / F      Filter ports by name / Clear filter", "color": "cyan"},
                {"text": "n / N               Ports paging next/prev", "color": "cyan"},
                {"text": "ms name = expr      Create condition signal (also: ms name expr)", "color": "magenta"},
                {"text": "Examples: ms valid = (1||2)&&3 | ms active = (I_DATA||I_DEN)&&I_HSYNC", "color": "magenta"},
                {"text": "Supports bit selects: A[0], A[1:0], [1] I_DATA[2:0]", "color": "magenta"},
                {"text": "Up/Down             Command history", "color": "white"},
                {"text": "Tab                 Path candidates popup; auto-complete common prefix", "color": "white"},
                {"text": "Esc/q               Close help", "color": "white"}
            ],
        }
    ]


_COLOR_NAME_TO_CURSES = {
    "black": curses.COLOR_BLACK,
    "red": curses.COLOR_RED,
    "green": curses.COLOR_GREEN,
    "yellow": curses.COLOR_YELLOW,
    "blue": curses.COLOR_BLUE,
    "magenta": curses.COLOR_MAGENTA,
    "cyan": curses.COLOR_CYAN,
    "white": curses.COLOR_WHITE,
}

_PAIR_BY_NAME: Dict[str, int] = {}


def _init_color_pairs() -> None:
    # Initialize pairs for supported colors with default background
    pair_id = 1
    for name, c in _COLOR_NAME_TO_CURSES.items():
        try:
            curses.init_pair(pair_id, c, -1)
            _PAIR_BY_NAME[name] = pair_id
            pair_id += 1
        except curses.error:
            # Some terminals may not support many pairs; ignore
            pass


def _highlight_ms_help() -> None:
    # Set global highlight term to 'ms' to draw attention in help overlay
    global _OVERLAY_HL_TERM
    _OVERLAY_HL_TERM = "ms"


def _set_help_filter_cmd(cmd_key: Optional[str]) -> None:
    global _OVERLAY_FILTER_CMD
    _OVERLAY_FILTER_CMD = cmd_key


def _set_error_message(msg: str) -> None:
    global _ERROR_MESSAGE
    _ERROR_MESSAGE = msg


def _find_help_page_index(pages: List[Dict[str, Any]], key: Optional[str]) -> int:
    if not key:
        return 0
    for i, p in enumerate(pages):
        if p.get("key") == key:
            return i
    return 0


def _render_help_overlay(stdscr: "curses._CursesWindow", pages: List[Dict[str, Any]], page_idx: int, scroll: int) -> None:
    max_y, max_x = stdscr.getmaxyx()
    # Frame
    stdscr.box()
    # Title
    try:
        title = pages[page_idx % len(pages)].get("title", "Help") if pages else "Help"
        label = f" {title} (Tab/Shift-Tab pages, Esc/q close) "
        if max_x > len(label) + 2:
            stdscr.addnstr(0, 2, label, max_x - 4, curses.A_BOLD)
    except curses.error:
        pass

    # Content area
    inner_h = max_y - 4
    inner_w = max_x - 4
    items = []
    current_page = pages[page_idx % len(pages)] if pages else {}
    center_mode = bool(current_page.get("center"))
    if pages:
        raw_items = current_page.get("items", [])
        # Optional filter to only show entries relevant to a specific command
        if _OVERLAY_FILTER_CMD and raw_items and isinstance(raw_items[0], dict) and ("cmd" in raw_items[0]):
            items = [it for it in raw_items if str(it.get("cmd",""))[:2].lower() == _OVERLAY_FILTER_CMD[:2].lower()]
            if not items:
                items = raw_items
        else:
            items = raw_items
    # Decide rendering mode: 3-col if items have 'cmd'
    three_col = bool(items and isinstance(items[0], dict) and ("cmd" in items[0]))
    # Zebra stripe drawing
    start = max(0, scroll)
    end = min(len(items), start + inner_h)
    if three_col:
        # Column widths: Command | Example | Description
        cmd_w = max(14, inner_w // 4)
        ex_w = max(18, inner_w // 3)
        desc_w = max(10, inner_w - cmd_w - ex_w - 2)
        # Header
        try:
            stdscr.addnstr(1, 2, _truncate("Command", cmd_w), cmd_w, curses.A_BOLD)
            stdscr.addnstr(1, 3 + cmd_w, _truncate("Example", ex_w), ex_w, curses.A_BOLD)
            stdscr.addnstr(1, 4 + cmd_w + ex_w, _truncate("Description", desc_w), desc_w, curses.A_BOLD)
        except curses.error:
            pass
        row_line = 0
        vis_rows = inner_h - 1
        for idx in range(start, end):
            if row_line >= vis_rows:
                break
            it = items[idx]
            cmd = _safe_str(it.get("cmd", ""))
            ex = _safe_str(it.get("example", ""))
            desc = _safe_str(it.get("desc", ""))
            # Colors
            cmd_pair = curses.color_pair(_PAIR_BY_NAME.get(it.get("cmd_color", "cyan"), 0)) | curses.A_BOLD
            ex_pair = curses.color_pair(_PAIR_BY_NAME.get(it.get("example_color", "yellow"), 0))
            ds_pair = curses.color_pair(_PAIR_BY_NAME.get(it.get("desc_color", "white"), 0))
            # Zebra by item index
            zebra_attr = curses.A_DIM if ((idx - start) % 2 == 1) else 0
            # Render line
            y = 2 + row_line
            try:
                stdscr.addnstr(y, 2, _truncate(cmd, cmd_w), cmd_w, cmd_pair | zebra_attr)
                stdscr.addnstr(y, 3 + cmd_w, _truncate(ex, ex_w), ex_w, ex_pair | zebra_attr)
                # Highlight term inside desc if set
                hl_term = _OVERLAY_HL_TERM or ""
                if hl_term and hl_term.lower() in desc.lower():
                    stdscr.addnstr(y, 4 + cmd_w + ex_w, _truncate(desc, desc_w), desc_w, ds_pair | zebra_attr)
                    try:
                        from re import finditer
                        for m in finditer(hl_term, desc):
                            sx = 4 + cmd_w + ex_w + m.start()
                            seg = desc[m.start():m.end()]
                            stdscr.addnstr(y, sx, _truncate(seg, desc_w - m.start()), desc_w - m.start(), curses.A_REVERSE)
                    except Exception:
                        pass
                else:
                    stdscr.addnstr(y, 4 + cmd_w + ex_w, _truncate(desc, desc_w), desc_w, ds_pair | zebra_attr)
            except curses.error:
                pass
            row_line += 1
            # separator line if room
            if row_line < vis_rows:
                try:
                    sep_y = 2 + row_line
                    stdscr.addnstr(sep_y, 2, "\u2500" * (inner_w), inner_w, curses.A_DIM)
                except curses.error:
                    pass
                row_line += 1
    else:
        for row, idx in enumerate(range(start, end)):
            item = items[idx]
            text = _safe_str(item.get("text", ""))
            color_name = _safe_str(item.get("color", "white")).lower()
            pair = curses.color_pair(_PAIR_BY_NAME.get(color_name, _PAIR_BY_NAME.get("white", 0)))
            # Alternate brightness via A_DIM every other line (approx ~10% visual change)
            attr = pair | (curses.A_DIM if (row % 2 == 1) else 0)
            # Highlight term if requested
            try:
                from re import finditer
                hl_term = _OVERLAY_HL_TERM or ""
                if hl_term and hl_term.lower() in text.lower():
                    # draw line base
                    if center_mode:
                        cx = max(2, 2 + (inner_w - len(text)) // 2)
                        stdscr.addnstr(2 + row, cx, _truncate(text, inner_w), inner_w, attr)
                    else:
                        stdscr.addnstr(2 + row, 2, _truncate(text, inner_w), inner_w, attr)
                    # overlay highlights (best-effort; may clip)
                    for m in finditer(hl_term, text, flags=0):
                        start_x = (2 + (inner_w - len(text)) // 2) + m.start() if center_mode else 2 + m.start()
                        seg = text[m.start():m.end()]
                        stdscr.addnstr(2 + row, start_x, _truncate(seg, inner_w - (start_x - 2)), inner_w - (start_x - 2), curses.A_REVERSE)
                    continue
            except Exception:
                pass
            try:
                if center_mode:
                    cx = max(2, 2 + (inner_w - len(text)) // 2)
                    stdscr.addnstr(2 + row, cx, _truncate(text, inner_w), inner_w, attr)
                else:
                    stdscr.addnstr(2 + row, 2, _truncate(text, inner_w), inner_w, attr)
            except curses.error:
                pass

    # Footer: error area (red) + instructions
    err = _ERROR_MESSAGE or ""
    footer_instr = "n/N: next/prev page   Up/Down,PgUp/PgDn: scroll   q or Esc: close"
    try:
        # Error message (red) on second-to-last row if present
        if err:
            stdscr.addnstr(max_y - 2, 2, _truncate(err, max_x - 4), max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
        stdscr.addnstr(max_y - 1, 2, _truncate(footer_instr, max_x - 4), max_x - 4, curses.A_BOLD)
    except curses.error:
        pass


# ---------------------------- SESSIONS -------------------------------------

def _sessions_dir() -> Path:
    d = (_THIS_DIR / ".." / "out" / "sessions").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_sessions() -> List[Dict[str, Any]]:
    d = _sessions_dir()
    sessions: List[Dict[str, Any]] = []
    for p in sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["_path"] = str(p)
            sessions.append(obj)
        except Exception:
            continue
    return sessions


def _save_session_snapshot(state: AppState) -> None:
    d = _sessions_dir()
    sid = state.session_id or f"session_{os.getpid()}"
    state.session_id = sid
    data = {
        "rtl_start": str(state.rtl_start) if state.rtl_start else "",
        "target_module": state.target_module or "",
        "excel_path": str(state.excel_path) if state.excel_path else "",
        "out_dir": str(state.out_dir),
    }
    path = d / f"{sid}.json"
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _shorten_path_for_display(p: str, max_width: int, keep_segments: int = 2) -> str:
    p = str(p)
    if len(p) <= max_width:
        return p
    parts = p.replace("\\", "/").split("/")
    tail = "/".join([seg for seg in parts if seg][:][-keep_segments:])
    base = "…/" + tail if tail else p[-max_width:]
    return _truncate(base, max_width)


def _wrap_text(s: str, width: int) -> List[str]:
    if width <= 0:
        return [""]
    s = s or ""
    lines: List[str] = []
    i = 0
    n = len(s)
    while i < n:
        lines.append(s[i:i+width])
        i += width
    if not lines:
        lines = [""]
    return lines

def _draw_ascii_box(stdscr: "curses._CursesWindow", top: int, left: int, height: int, width: int) -> None:
    if height < 2 or width < 2:
        return
    try:
        # Use curses box-drawing where possible
        horiz = "─"
        vert = "│"
        tl = "┌"
        tr = "┐"
        bl = "└"
        br = "┘"
        # Top border
        stdscr.addnstr(top, left, tl + (horiz * (width - 2)) + tr, width)
        # Middle
        for y in range(top + 1, top + height - 1):
            stdscr.addnstr(y, left, vert, 1)
            stdscr.addnstr(y, left + width - 1, vert, 1)
        # Bottom border
        stdscr.addnstr(top + height - 1, left, bl + (horiz * (width - 2)) + br, width)
    except curses.error:
        pass


def _run_session_chooser(stdscr: "curses._CursesWindow", sessions: List[Dict[str, Any]]) -> Optional[Union[Dict[str, Any], str]]:
    # Command-driven chooser: new | <number> | f <substr> | n/N | del <number> | del all | q
    filter_text = ""
    page = 0
    compl_items: List[Tuple[str, bool]] = []  # for optional candidate display (kept empty here)
    while True:
        max_y, max_x = stdscr.getmaxyx()
        # Aggressive clear to avoid ghosting from previous screens
        try:
            stdscr.clear()
        except Exception:
            stdscr.erase()
        # Banner: title + version + ASCII art + one-line guide
        banner = [
            "    _                      _   _                ____            ",
            "   / \\   ___ ___  ___ _ __| |_(_) ___  _ __    / ___| ___ _ __  ",
            "  / _ \\ / __/ __|/ _ \\ '__| __| |/ _ \\| '_ \\  | |  _ / _ \\ '_ \\",
            " / ___ \\\\__ \\__ \\  __/ |  | |_| | (_) | | | | | |_| |  __/ | | |",
            "/_/   \\_\\\__/___/\\___|_|   \\__|_|\\___/|_| |_|  \\____|\\___|_| |_|",
        ]
        guide = "Type new to start, a number to load, f <text> to filter, n/N to page, q to quit."
        y = 0
        # Draw ASCII art centered as a block to avoid per-line rounding shifts
        ascii_width = max(len(line) for line in banner)
        base_x = 2 + max(0, (max_x - 4 - ascii_width) // 2)
        last_line_len = 0
        last_line_x = base_x
        for line in banner:
            try:
                stdscr.addnstr(y, base_x, _truncate(line, max_x - 4 - base_x + 2), max_x - 4 - base_x + 2)
            except curses.error:
                pass
            last_line_len = len(line)
            y += 1
        # Render version tag at the right side of the last ASCII line
        try:
            ver_text = f" { _APP_VERSION } "
            ver_x = min(max_x - 2 - len(ver_text), last_line_x + last_line_len + 1)
            if ver_x > 2:
                stdscr.addnstr(y - 1, ver_x, _truncate(ver_text, max_x - 4), max_x - 4, curses.A_DIM | curses.A_BOLD)
        except curses.error:
            pass
        # One blank line after banner; guide will render just above box below
        y += 1

        # Create boxed list area below banner with horizontal margins
        # Reserve 3 lines: hint, prompt (with '>'), and a trailing blank to avoid clipping
        min_reserved = 3
        list_y = y + 1
        if max_y - list_y - min_reserved < 5:
            list_y = max(1, max_y - (min_reserved + 6))
        list_margin_x = 2
        list_w = max(20, max_x - (list_margin_x * 2))
        # Clamp
        if list_margin_x + list_w > max_x:
            list_w = max(20, max_x - list_margin_x - 1)
        list_h = max(6, max_y - list_y - min_reserved)
        if list_y + list_h > max_y:
            list_h = max(6, max_y - list_y - 1)
        inner_w = list_w - 4
        # Draw guide directly above the list box
        try:
            stdscr.addnstr(max(1, list_y - 1), list_margin_x + 2, _truncate(guide, max_x - 4 - list_margin_x), max_x - 4 - list_margin_x, curses.A_DIM)
        except curses.error:
            pass
        # Show directory candidates popup immediately above the input line
        if compl_items:
            # Build popup window sized to content and ensure visibility
            max_cols = min(3, max(1, max_x // 20))
            items = [nm + ("/" if is_dir else "") for (nm, is_dir) in compl_items[:24]]
            col_w = max(8, max((len(s) for s in items), default=8)) + 2
            cols = min(max_cols, max(1, (max_x - 4) // col_w))
            rows = max(1, (len(items) + cols - 1) // cols)
            win_w = min(max_x, 2 + cols * col_w + 2)
            win_h = min(rows + 2, 10)
            # Place directly above the prompt line (which is max_y-2)
            win_y = max(1, (max_y - 2) - win_h)
            win_x = 0
            try:
                pop = curses.newwin(win_h, win_w, win_y, win_x)
                pop.box()
                try:
                    pop.addnstr(0, 2, _truncate(" Candidates ", win_w - 4), win_w - 4, curses.A_BOLD)
                except curses.error:
                    pass
                idx = 0
                for r in range(1, win_h - 1):
                    for c in range(cols):
                        if idx >= len(items):
                            break
                        label = items[idx]
                        x = 1 + c * col_w + 1
                        try:
                            pop.addnstr(r, x, _truncate(label, col_w - 1), col_w - 1, curses.color_pair(_PAIR_BY_NAME.get("cyan",0)))
                        except curses.error:
                            pass
                        idx += 1
                pop.refresh()
            except curses.error:
                pass
        # Draw ASCII box directly on stdscr
        _draw_ascii_box(stdscr, list_y, list_margin_x, list_h, list_w)
        # Column header inside list window
        no_w = 6
        mod_w = max(12, inner_w // 5)
        rtl_w = max(18, inner_w // 3)
        xls_w = max(12, inner_w // 6)
        out_w = max(10, inner_w - no_w - mod_w - rtl_w - xls_w - 3)
        try:
            stdscr.addnstr(list_y + 1, list_margin_x + 2, _truncate("No", no_w), no_w, curses.A_BOLD)
            stdscr.addnstr(list_y + 1, list_margin_x + 2 + no_w + 1, _truncate("Module", mod_w), mod_w, curses.A_BOLD)
            stdscr.addnstr(list_y + 1, list_margin_x + 2 + no_w + 1 + mod_w + 1, _truncate("RTL", rtl_w), rtl_w, curses.A_BOLD)
            stdscr.addnstr(list_y + 1, list_margin_x + 2 + no_w + 1 + mod_w + 1 + rtl_w + 1, _truncate("Excel", xls_w), xls_w, curses.A_BOLD)
            stdscr.addnstr(list_y + 1, list_margin_x + 2 + no_w + 1 + mod_w + 1 + rtl_w + 1 + xls_w + 1, _truncate("Out", out_w), out_w, curses.A_BOLD)
        except curses.error:
            pass
        # Filter and paginate
        filtered = sessions
        if filter_text:
            ft = filter_text.lower()
            def _m(s: Dict[str, Any]) -> str:
                return f"{s.get('rtl_start','')} {s.get('target_module','')} {s.get('excel_path','')} {s.get('out_dir','')}".lower()
            filtered = [s for s in sessions if ft in _m(s)]
        list_inner_h = list_h - 3  # rows available for list within window
        page_size = max(1, list_inner_h - 1)
        start = page * page_size
        end = min(len(filtered), start + page_size)
        # Rows with variable height (wrap RTL)
        y_ptr = list_y + 2
        y_limit = list_y + list_h - 1
        idx = start
        row_index = 0
        while idx < len(filtered) and y_ptr < y_limit:
            s = filtered[idx]
            num = f"[{idx + 1}]"
            module = s.get('target_module', '') or ''
            rtl_full = s.get('rtl_start', '') or ''
            xls = os.path.basename(s.get('excel_path', '') or '')
            outp = _shorten_path_for_display(s.get('out_dir', '') or '', out_w)
            rtl_lines = _wrap_text(rtl_full, rtl_w)
            row_h = max(1, len(rtl_lines))
            if y_ptr + row_h > y_limit:
                break
            zebra = curses.A_DIM if (row_index % 2) else 0
            try:
                # number (cyan)
                stdscr.addnstr(y_ptr, list_margin_x + 2, _truncate(num, no_w), no_w, curses.color_pair(_PAIR_BY_NAME.get('cyan',0)) | curses.A_BOLD)
                # module (green bold)
                stdscr.addnstr(y_ptr, list_margin_x + 2 + no_w + 1, _truncate(module, mod_w), mod_w, curses.color_pair(_PAIR_BY_NAME.get('green',0)) | curses.A_BOLD | zebra)
                # rtl (wrap)
                for li, rline in enumerate(rtl_lines[:row_h]):
                    stdscr.addnstr(y_ptr + li, list_margin_x + 2 + no_w + 1 + mod_w + 1, _truncate(rline, rtl_w), rtl_w, zebra)
                # excel (yellow) and out shown on first line of the row
                stdscr.addnstr(y_ptr, list_margin_x + 2 + no_w + 1 + mod_w + 1 + rtl_w + 1, _truncate(xls, xls_w), xls_w, curses.color_pair(_PAIR_BY_NAME.get('yellow',0)) | zebra)
                stdscr.addnstr(y_ptr, list_margin_x + 2 + no_w + 1 + mod_w + 1 + rtl_w + 1 + xls_w + 1, _truncate(outp, out_w), out_w, zebra)
            except curses.error:
                pass
            y_ptr += row_h
            idx += 1
            row_index += 1
        # Empty-state message
        if len(filtered) == 0:
            msg = "No previous sessions. Type 'new' to start."
            try:
                stdscr.addnstr(list_y + 3, list_margin_x + 2, _truncate(msg, inner_w), inner_w, curses.A_DIM)
            except curses.error:
                pass
        # Hints block (color-coded) on the line above the prompt
        hint_y = max_y - 3
        try:
            # Clear hint line fully before writing
            stdscr.addnstr(hint_y, 0, " " * max_x, max_x)
            x = 2
            def seg(text, color=None, bold=False):
                nonlocal x
                attr = curses.A_BOLD if bold else 0
                if color:
                    attr |= curses.color_pair(_PAIR_BY_NAME.get(color,0))
                stdscr.addnstr(hint_y, x, text, max_x - x - 2, attr)
                x += len(text) + 1
            seg("Type:", None, True)
            seg("new", "cyan", True); seg("start new session")
            seg("|")
            seg("<number>", "cyan", True); seg("load session")
            seg("|")
            seg("f <text>", "cyan", True); seg("filter")
            seg("|")
            seg("n/N", "cyan", True); seg("page")
            seg("|")
            seg("del <numbers | all>", "cyan", True); seg("delete")
            seg("|")
            seg("q", "white", True); seg("quit")
        except curses.error:
            pass
        # Prompt (one line below hint, not on the very last line)
        prompt = "> "
        try:
            # Clear prompt line fully to avoid residual characters
            stdscr.addnstr(max_y - 2, 0, " " * max_x, max_x)
            # Place prompt one visual line below hint
            stdscr.addstr(max_y - 2, 0, prompt)
        except curses.error:
            pass
        stdscr.refresh()
        # Read line
        curses.echo()
        try:
            cmdline = stdscr.getstr(max_y - 2, len(prompt), max(8, max_x - len(prompt) - 2)).decode(errors='ignore').strip()
        except Exception:
            cmdline = ""
        curses.noecho()
        if not cmdline:
            continue
        low = cmdline.lower()
        if low == "q":
            return None
        if low == "new":
            return "new"
        if low.startswith("f "):
            filter_text = cmdline[2:].strip()
            page = 0
            continue
        if low == "n":
            page += 1
            continue
        if cmdline == "N":
            page = max(0, page - 1)
            continue
        if cmdline.isdigit():
            idx = int(cmdline)
            if 1 <= idx <= len(filtered):
                return filtered[idx - 1]
            continue
        # del command: del <number(s)> or del all
        if low.startswith("del "):
            args = cmdline[4:].strip()
            if args == "all":
                # Delete all sessions with confirmation
                # Show all sessions highlighted and ask for confirmation
                try:
                    stdscr.clear()
                    max_y, max_x = stdscr.getmaxyx()
                    # Show banner
                    stdscr.addnstr(0, 2, "DELETE ALL SESSIONS - Confirmation Required", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
                    stdscr.addnstr(2, 2, f"You are about to delete {len(sessions)} session(s).", max_x - 4)
                    stdscr.addnstr(3, 2, "Type 'y' to confirm, any other key to cancel.", max_x - 4, curses.A_BOLD)
                    stdscr.refresh()
                    
                    curses.echo()
                    confirm = stdscr.getch()
                    curses.noecho()
                    
                    if confirm in (ord('y'), ord('Y')):
                        for s in sessions:
                            path = s.get("_path")
                            if path and Path(path).exists():
                                Path(path).unlink()
                        sessions.clear()
                        filtered = []
                        page = 0
                        # Show success message
                        stdscr.addnstr(5, 2, "All sessions deleted!", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("green",0)) | curses.A_BOLD)
                        stdscr.refresh()
                        import time
                        time.sleep(1)
                    else:
                        # Cancelled
                        stdscr.addnstr(5, 2, "Delete cancelled.", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("yellow",0)))
                        stdscr.refresh()
                        import time
                        time.sleep(1)
                except Exception as e:
                    # Show error message
                    try:
                        stdscr.addnstr(max_y - 4, 2, f"Error: {str(e)}", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
                        stdscr.refresh()
                        import time
                        time.sleep(1)
                    except curses.error:
                        pass
                continue
            else:
                # Parse multiple numbers: "del 2 3 4" or "del 2,3,4" or "del 2"
                # Support both space and comma separators
                args_normalized = args.replace(',', ' ')
                tokens = args_normalized.split()
                indices = []
                for tok in tokens:
                    if tok.isdigit():
                        idx = int(tok)
                        if 1 <= idx <= len(filtered):
                            indices.append(idx)
                
                if not indices:
                    # Invalid input
                    try:
                        stdscr.addnstr(max_y - 4, 2, "Invalid session number(s)", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
                        stdscr.refresh()
                        import time
                        time.sleep(1)
                    except curses.error:
                        pass
                    continue
                
                # Remove duplicates and sort
                indices = sorted(list(set(indices)))
                
                # Show confirmation with highlighted sessions
                try:
                    stdscr.clear()
                    max_y, max_x = stdscr.getmaxyx()
                    
                    # Banner
                    stdscr.addnstr(0, 2, f"DELETE {len(indices)} SESSION(S) - Confirmation Required", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
                    
                    # Show the sessions to be deleted (highlighted)
                    y_pos = 2
                    stdscr.addnstr(y_pos, 2, "Sessions to be deleted:", max_x - 4, curses.A_BOLD)
                    y_pos += 1
                    
                    # Limit display to prevent overflow
                    display_limit = min(len(indices), max_y - 8)
                    for i, idx in enumerate(indices[:display_limit]):
                        if y_pos >= max_y - 4:
                            break
                        s = filtered[idx - 1]
                        module = s.get('target_module', '') or 'N/A'
                        rtl = s.get('rtl_start', '') or 'N/A'
                        # Shorten paths for display
                        if len(rtl) > 40:
                            rtl = "..." + rtl[-37:]
                        line = f"  [{idx}] {module} - {rtl}"
                        stdscr.addnstr(y_pos, 2, _truncate(line, max_x - 4), max_x - 4, 
                                      curses.color_pair(_PAIR_BY_NAME.get("yellow",0)) | curses.A_BOLD)
                        y_pos += 1
                    
                    if len(indices) > display_limit:
                        stdscr.addnstr(y_pos, 2, f"  ... and {len(indices) - display_limit} more", max_x - 4, curses.A_DIM)
                        y_pos += 1
                    
                    # Confirmation prompt
                    y_pos += 1
                    stdscr.addnstr(y_pos, 2, "Type 'y' to confirm deletion, any other key to cancel.", max_x - 4, curses.A_BOLD)
                    stdscr.refresh()
                    
                    # Wait for confirmation
                    confirm = stdscr.getch()
                    
                    if confirm in (ord('y'), ord('Y')):
                        # Delete in reverse order to maintain indices
                        deleted_count = 0
                        for idx in reversed(indices):
                            try:
                                s = filtered[idx - 1]
                                path = s.get("_path")
                                if path and Path(path).exists():
                                    Path(path).unlink()
                                # Remove from sessions list
                                sessions.remove(s)
                                deleted_count += 1
                            except Exception:
                                pass
                        
                        # Update filtered list
                        if filter_text:
                            ft = filter_text.lower()
                            def _m(s: Dict[str, Any]) -> str:
                                return f"{s.get('rtl_start','')} {s.get('target_module','')} {s.get('excel_path','')} {s.get('out_dir','')}".lower()
                            filtered = [s for s in sessions if ft in _m(s)]
                        else:
                            filtered = sessions
                        
                        # Show success message
                        y_pos += 2
                        msg = f"{deleted_count} session(s) deleted successfully!"
                        stdscr.addnstr(y_pos, 2, msg, max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("green",0)) | curses.A_BOLD)
                        stdscr.refresh()
                        import time
                        time.sleep(1)
                    else:
                        # Cancelled
                        y_pos += 2
                        stdscr.addnstr(y_pos, 2, "Delete cancelled.", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("yellow",0)))
                        stdscr.refresh()
                        import time
                        time.sleep(1)
                        
                except Exception as e:
                    # Show error message
                    try:
                        stdscr.clear()
                        stdscr.addnstr(2, 2, f"Error: {str(e)}", max_x - 4, curses.color_pair(_PAIR_BY_NAME.get("red",0)) | curses.A_BOLD)
                        stdscr.refresh()
                        import time
                        time.sleep(2)
                    except curses.error:
                        pass
                continue
        # Unknown
        continue


def _first_time_popup_and_autoscan(stdscr: "curses._CursesWindow", state: AppState) -> None:
    max_y, max_x = stdscr.getmaxyx()
    h = 9
    w = min(70, max_x - 8)
    y = (max_y - h) // 2
    x = (max_x - w) // 2
    win = curses.newwin(h, w, y, x)
    win.box()
    msg_lines = [
        "First time detected.",
        "No previous session data.",
        "We'll run an initial RTL scan to get started.",
        "Press Enter to proceed.",
    ]
    for i, t in enumerate(msg_lines):
        try:
            win.addnstr(1 + i, 2, _truncate(t, w - 4), w - 4, curses.A_BOLD if i == 0 else 0)
        except curses.error:
            pass
    win.refresh()
    while True:
        ch = win.getch()
        if ch in (10, 13, 27):
            break
    # Attempt auto-scan if rtl_start is set via env or heuristics else skip
    # Heuristic: EDA/RTL under repo root
    repo_root = _THIS_DIR.parent
    candidate = repo_root / "EDA" / "RTL"
    if candidate.exists():
        state.rtl_start = candidate
        try:
            modules, mi, occs = build_context_from_rtl(candidate, None)
            state.modules_db = modules
            state.module_info = mi
            state.target_module = mi.module
            state.occs = occs
        except Exception:
            pass
    # Auto-find excel in Data folder if present
    auto_excel = _auto_find_excel()
    if auto_excel:
        state.excel_path = auto_excel


def _auto_find_excel() -> Optional[Path]:
    """Data 폴더에서 'Assertion_TF.xlsx'를 우선 탐색, 없으면 첫 번째 xlsx 반환"""
    data_dir = _THIS_DIR.parent / "Data"
    if not data_dir.exists():
        return None
    try:
        # 1순위: Assertion_TF.xlsx (reference 파일)
        preferred = data_dir / "Assertion_TF.xlsx"
        if preferred.exists() and not preferred.name.startswith("~$"):
            return preferred.resolve()
        
        # 2순위: 정렬된 첫 번째 xlsx 파일 (세션 파일 제외)
        for x in sorted(data_dir.glob("*.xlsx")):
            # 임시 파일과 타임스탬프가 포함된 세션 파일 건너뛰기
            if x.name.startswith("~$") or "-20" in x.name:
                continue
            return x.resolve()
    except Exception:
        return None
    return None


# ---------------------- Condition Signal Parsing ---------------------------

def _tokenize_expr(expr: str) -> List[str]:
    # Tokenize a subset of SystemVerilog operators sufficient for validation
    # Multi-char ops first to avoid partial matches
    ops = [
        "<<<", ">>>", "===", "!==", "<<", ">>", "<=", ">=", "==", "!=", "&&", "||", "**",
    ]
    singles = list("&|^~!+-*/%<>()[]{}?:=,;")
    s = expr
    for op in ops:
        s = s.replace(op, f" {op} ")
    for ch in singles:
        s = s.replace(ch, f" {ch} ")
    # Collapse spaces and split
    return [t for t in s.split() if t]


def _is_identifier(tok: str) -> bool:
    if not tok:
        return False
    if tok[0].isalpha() or tok[0] == "_":
        return all(c.isalnum() or c == "_" for c in tok)
    return tok.isdigit()  # allow numeric aliases like 1,2,3


def _resolve_signal_refs(state: AppState) -> Dict[str, Dict[str, Any]]:
    # Build a dictionary of known signals including ports and existing conditions
    refs: Dict[str, Dict[str, Any]] = {}
    all_ports = state.module_info.inputs + state.module_info.outputs + state.module_info.inouts
    for p in all_ports:
        name = p.get("name", "")
        if name:
            refs[name] = p
    # Numeric aliases: 1,2,3... map to concatenated list order
    for idx, p in enumerate(all_ports, start=1):
        refs[str(idx)] = p
    for c in state.conditions:
        nm = c.get("name", "")
        if nm:
            refs[nm] = {"name": nm, "width": 1}
    return refs


def _condition_deps(expr: str, state: AppState) -> List[str]:
    """Return list of condition-signal names referenced by this expr."""
    names = {c.get("name", "") for c in state.conditions}
    toks = _tokenize_expr(expr)
    deps: List[str] = []
    for t in toks:
        if t in names:
            deps.append(t)
    return deps


def _has_cycle_with_new(name: str, expr: str, state: AppState) -> bool:
    """Detect cycle if we add condition `name` with `expr` to existing graph."""
    # Build adjacency: existing + proposed
    adj: Dict[str, List[str]] = {}
    for c in state.conditions:
        nm = c.get("name", "")
        if not nm:
            continue
        adj[nm] = _condition_deps(c.get("expr", ""), state)
    adj[name] = _condition_deps(expr, state)

    # DFS cycle check from `name`
    seen: set[str] = set()
    stack: set[str] = set()

    def dfs(n: str) -> bool:
        if n in stack:
            return True
        if n in seen:
            return False
        seen.add(n)
        stack.add(n)
        for m in adj.get(n, []):
            if dfs(m):
                return True
        stack.remove(n)
        return False

    return dfs(name)


def _validate_condition_expr(expr: str, state: AppState) -> Tuple[bool, str]:
    tokens = _tokenize_expr(expr)
    refs = _resolve_signal_refs(state)
    stack: List[str] = []
    i = 0
    try:
        brace_stack = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in ("(",")"):
                if tok == "(":
                    stack.append(tok)
                else:
                    if not stack or stack.pop() != "(":
                        return False, "unmatched ')'"
                i += 1
                continue
            if tok == "{":
                brace_stack += 1
                i += 1
                continue
            if tok == "}":
                if brace_stack == 0:
                    return False, "unmatched '}'"
                brace_stack -= 1
                i += 1
                continue
            if tok in ("&&","||","&","|","^","~","!","+","-","*","/","%","<",
                        ">","<=",">=","==","!=","===","!==","<<",">>","<<<",
                        ">>>","?",":","**","=",")",";",","):
                i += 1
                continue
            # Bit select forms: NAME [ idx ] or NAME [ msb : lsb ] or [1] NAME[2:0]
            if tok == "[":
                # Leading bracket case: [1] NAME...
                # We accept but ignore the literal select for validation
                j = i + 1
                while j < len(tokens) and tokens[j] != "]":
                    j += 1
                if j >= len(tokens):
                    return False, "unmatched ']'"
                i = j + 1
                continue
            # Identifier possibly followed by selection
            if _is_identifier(tok):
                name = tok
                if name not in refs:
                    return False, f"unknown signal '{name}'"
                # Optional selection: [ ... ]
                j = i + 1
                if j < len(tokens) and tokens[j] == "[":
                    k = j + 1
                    while k < len(tokens) and tokens[k] != "]":
                        k += 1
                    if k >= len(tokens):
                        return False, "unmatched ']'"
                    i = k + 1
                else:
                    i = j
                continue
            return False, f"unexpected token '{tok}'"
        if stack:
            return False, "unclosed '('"
        return True, ""
    except Exception as e:
        return False, str(e)


# ---------------------- Path completion utilities --------------------------

def _path_complete(line: str, cursor_pos: int) -> Tuple[str, int, List[Tuple[str, bool]], str]:
    # Find the token at cursor that looks like a path (after 'set rtl' or 'set excel'/'set out')
    head = line[:cursor_pos]
    tail = line[cursor_pos:]
    toks = head.split()
    if len(toks) < 2:
        return line, cursor_pos, [], ""
    cmd = toks[0]
    if cmd != "set" or len(toks) < 3:
        return line, cursor_pos, [], ""
    # The third token onwards form the path prefix
    # Support spaces inside path by taking substring after 'set <key> '
    try:
        key = toks[1]
        prefix_start = head.index(key, head.index("set") + 3) + len(key) + 1
    except ValueError:
        return line, cursor_pos, [], ""
    path_prefix = head[prefix_start:].lstrip()
    if not path_prefix:
        path_prefix = ""
    # Expanduser/vars
    expanded = os.path.expandvars(os.path.expanduser(path_prefix))
    # Treat both '/' and '\\' as directory separators for completion logic
    sep_end = expanded.endswith('/') or expanded.endswith('\\')
    base_dir = Path(expanded).parent if not sep_end else Path(expanded)
    if str(base_dir) == "":
        base_dir = Path(".")
    try:
        entries: List[Tuple[str, bool]] = []
        if base_dir.exists():
            for p in sorted(base_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if p.name.startswith('.'):
                    continue
                if p.name.startswith('$') or p.name.startswith(':'):
                    continue
                if p.name.startswith("~$"):
                    continue
                # match prefix last segment
                last = Path(expanded).name
                if sep_end or p.name.lower().startswith(last.lower() if last else ""):
                    entries.append((p.name, p.is_dir()))
        # compute common prefix to auto-complete
        common = _common_prefix([e[0] for e in entries if e[0]]) if entries else ""
        if common:
            # replace the last segment in line with common
            new_prefix = os.path.join(str(base_dir), common)
            new_head = head[:prefix_start] + new_prefix
            return new_head + tail, len(new_head), entries, str(base_dir)
        return line, cursor_pos, entries, str(base_dir)
    except Exception:
        return line, cursor_pos, [], ""


def _path_complete_raw(line: str, cursor_pos: int) -> Tuple[str, int, List[Tuple[str, bool]], str]:
    # Treat the entire line up to cursor as a path prefix (used in onboarding stages)
    head = line[:cursor_pos]
    tail = line[cursor_pos:]
    try:
        prefix = head.strip()
        expanded = os.path.expandvars(os.path.expanduser(prefix))
        # If user typed nothing, start from CWD
        if expanded.strip() == "":
            expanded = os.getcwd()
        sep_end = expanded.endswith('/') or expanded.endswith('\\')
        base_dir = Path(expanded).parent if not sep_end else Path(expanded)
        if str(base_dir) == "":
            base_dir = Path(".")
        entries: List[Tuple[str, bool]] = []
        if base_dir.exists():
            for p in sorted(base_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if p.name.startswith('.'):
                    continue
                if p.name.startswith('$') or p.name.startswith(':'):
                    continue
                if p.name.startswith("~$"):
                    continue
                last = Path(expanded).name
                if sep_end or p.name.lower().startswith(last.lower() if last else ""):
                    entries.append((p.name, p.is_dir()))
        common = _common_prefix([e[0] for e in entries if e[0]]) if entries else ""
        if common:
            # Use forward slashes for consistency across platforms
            base_str = str(base_dir).rstrip("/\\").replace("\\", "/")
            new_prefix = (base_str + "/" + common) if base_str else common
            new_head = new_prefix
            return new_head + tail, len(new_head), entries, str(base_dir)
        return line, cursor_pos, entries, str(base_dir)
    except Exception:
        return line, cursor_pos, [], ""

def _common_prefix(names: List[str]) -> str:
    if not names:
        return ""
    s1 = min(names)
    s2 = max(names)
    i = 0
    while i < len(s1) and i < len(s2) and s1[i].lower() == s2[i].lower():
        i += 1
    return s1[:i]


# ---------------------- Assertion Wizard -----------------------------------

def _get_assertion_plugins_info() -> List[Dict[str, Any]]:
    """Get information about available assertion plugins."""
    from assertions import get_registered_plugins  # type: ignore
    plugins = get_registered_plugins()
    
    info_list = []
    for plugin_cls in plugins:
        plugin_info = {
            'name': plugin_cls.plugin_name,
            'sheet_name': plugin_cls.sheet_name,
            'description': _get_plugin_description(plugin_cls.plugin_name),
            'fields': _get_plugin_fields(plugin_cls.plugin_name),
        }
        info_list.append(plugin_info)
    return info_list


def _get_plugin_description(plugin_name: str) -> str:
    """Get description for each plugin type."""
    descriptions = {
        'counter': 'Generate counter-based assertions with increment/decrement/reset conditions',
        'handshake': 'Generate 2-phase or 4-phase handshake protocol assertions',
        'sequence': 'Generate temporal sequence assertions',
    }
    return descriptions.get(plugin_name, 'Custom assertion type')


def _get_plugin_fields(plugin_name: str) -> List[Dict[str, str]]:
    """Get required fields for each plugin type."""
    fields = {
        'counter': [
            {'name': 'counter_name', 'type': 'string', 'prompt': 'Counter name'},
            {'name': 'clock_edge', 'type': 'select', 'prompt': 'Clock edge', 'options': ['posedge', 'negedge']},
            {'name': 'clock_signal', 'type': 'port', 'prompt': 'Clock signal'},
            {'name': 'reset_edge', 'type': 'select', 'prompt': 'Reset edge', 'options': ['posedge', 'negedge', '']},
            {'name': 'reset_signal', 'type': 'port', 'prompt': 'Reset signal (or leave empty)'},
            {'name': 'increment_condition', 'type': 'string', 'prompt': 'Increment condition'},
            {'name': 'reset_condition', 'type': 'string', 'prompt': 'Reset condition'},
        ],
        'handshake': [
            {'name': 'phase_type', 'type': 'select', 'prompt': 'Handshake type', 'options': ['2phase', '4phase']},
            {'name': 'clock_signal', 'type': 'port', 'prompt': 'Base Clock'},
            {'name': 'reset_signal', 'type': 'port', 'prompt': 'Reset signal'},
            {'name': 'sender_signal', 'type': 'port', 'prompt': 'Sender (request) signal'},
            {'name': 'receiver_signal', 'type': 'port', 'prompt': 'Receiver (acknowledge) signal'},
        ],
    }
    return fields.get(plugin_name, [])


def _render_assertion_wizard(stdscr: "curses._CursesWindow", state: AppState) -> None:
    """Render assertion creation wizard."""
    max_y, max_x = stdscr.getmaxyx()
    
    # Title
    title = "Assertion Creator Wizard"
    try:
        stdscr.addnstr(0, 2, title, max_x - 4, curses.A_BOLD | curses.color_pair(_PAIR_BY_NAME.get("cyan", 0)))
    except curses.error:
        pass
    
    # Box for content
    margin_x = 2
    top = 2
    reserved_bottom = 5  # For prompt and hints
    box_h = max(10, max_y - top - reserved_bottom)
    box_w = max(40, max_x - (margin_x * 2))
    _draw_ascii_box(stdscr, top, margin_x, box_h, box_w)
    
    if state.assertion_wizard_stage == 'select_type':
        _render_type_selection(stdscr, state, top, margin_x, box_h, box_w)
    elif state.assertion_wizard_stage == 'input_data':
        _render_data_input(stdscr, state, top, margin_x, box_h, box_w)
    elif state.assertion_wizard_stage == 'confirm':
        _render_confirmation(stdscr, state, top, margin_x, box_h, box_w)


def _render_type_selection(stdscr: "curses._CursesWindow", state: AppState, top: int, margin_x: int, box_h: int, box_w: int) -> None:
    """Render assertion type selection screen."""
    plugins = _get_assertion_plugins_info()
    
    y = top + 2
    try:
        stdscr.addnstr(y, margin_x + 2, "Select Assertion Type:", box_w - 4, curses.A_BOLD)
        y += 2
    except curses.error:
        pass
    
    for i, plugin in enumerate(plugins, start=1):
        if y >= top + box_h - 2:
            break
        
        # Check if sheet exists in Excel (use session excel if available)
        sheet_status = ""
        excel_to_check = state.session_excel_path or state.excel_path
        if excel_to_check:
            try:
                from openpyxl import load_workbook  # type: ignore
                from assertions.base import BaseAssertionPlugin  # type: ignore
                wb = load_workbook(str(excel_to_check), read_only=True)
                # Check case-insensitively
                actual_sheet = BaseAssertionPlugin.find_sheet_case_insensitive(wb.sheetnames, plugin['sheet_name'])
                if actual_sheet:
                    sheet_status = f"✓ Sheet found: {actual_sheet}"
                    status_color = "green"
                else:
                    sheet_status = "✗ Sheet missing"
                    status_color = "red"
                wb.close()
            except Exception as e:
                sheet_status = f"? Cannot check: {str(e)[:20]}"
                status_color = "yellow"
        
        # Display option
        try:
            option_line = f"[{i}] {plugin['name'].upper()}"
            stdscr.addnstr(y, margin_x + 4, option_line, box_w - 6, curses.A_BOLD)
            y += 1
            
            desc_line = f"    {plugin['description']}"
            stdscr.addnstr(y, margin_x + 4, _truncate(desc_line, box_w - 6), box_w - 6, curses.A_DIM)
            y += 1
            
            if sheet_status:
                status_line = f"    Sheet: {plugin['sheet_name']} - {sheet_status}"
                color = _PAIR_BY_NAME.get(status_color, 0)
                stdscr.addnstr(y, margin_x + 4, _truncate(status_line, box_w - 6), box_w - 6, curses.color_pair(color))
                y += 1
            
            y += 1  # Blank line between options
        except curses.error:
            pass
    
    # Instructions
    try:
        y = top + box_h - 3
        inst_line = "Enter number to select, or 'cancel' to exit"
        stdscr.addnstr(y, margin_x + 2, inst_line, box_w - 4, curses.A_DIM)
    except curses.error:
        pass


def _render_data_input(stdscr: "curses._CursesWindow", state: AppState, top: int, margin_x: int, box_h: int, box_w: int) -> None:
    """Render data input screen for selected assertion type."""
    plugin_name = state.assertion_selected_type
    if not plugin_name:
        return
    
    plugins = _get_assertion_plugins_info()
    plugin = next((p for p in plugins if p['name'] == plugin_name), None)
    if not plugin:
        return
    
    fields = plugin['fields']
    y = top + 2
    
    try:
        title_line = f"Creating {plugin_name.upper()} Assertion"
        stdscr.addnstr(y, margin_x + 2, title_line, box_w - 4, curses.A_BOLD)
        y += 2
    except curses.error:
        pass
    
    # Show fields and current values
    for i, field in enumerate(fields):
        if y >= top + box_h - 4:
            break
        
        field_name = field['name']
        prompt = field['prompt']
        current_val = state.assertion_input_data.get(field_name, '')
        
        try:
            # Field prompt
            field_line = f"{i+1}. {prompt}:"
            stdscr.addnstr(y, margin_x + 4, field_line, box_w - 6, curses.A_BOLD)
            y += 1
            
            # Current value or options
            if field['type'] == 'select':
                options_str = ', '.join(field.get('options', []))
                opt_line = f"   Options: {options_str}"
                stdscr.addnstr(y, margin_x + 4, _truncate(opt_line, box_w - 6), box_w - 6, curses.A_DIM)
                y += 1
            elif field['type'] == 'port':
                hint_line = "   (Use port name or number from Input/Output list)"
                stdscr.addnstr(y, margin_x + 4, _truncate(hint_line, box_w - 6), box_w - 6, curses.A_DIM)
                y += 1
            
            # Current value display
            val_display = str(current_val) if current_val else "<not set>"
            val_line = f"   Current: {val_display}"
            val_color = "green" if current_val else "red"
            stdscr.addnstr(y, margin_x + 4, _truncate(val_line, box_w - 6), box_w - 6, curses.color_pair(_PAIR_BY_NAME.get(val_color, 0)))
            y += 1
            y += 1  # Blank line
        except curses.error:
            pass
    
    # Instructions
    try:
        y = top + box_h - 3
        inst_line = "Enter: set <field_num> <value> | 'done' to finish | 'cancel' to abort"
        stdscr.addnstr(y, margin_x + 2, _truncate(inst_line, box_w - 4), box_w - 4, curses.A_DIM)
    except curses.error:
        pass


def _render_confirmation(stdscr: "curses._CursesWindow", state: AppState, top: int, margin_x: int, box_h: int, box_w: int) -> None:
    """Render confirmation screen."""
    y = top + 2
    
    try:
        stdscr.addnstr(y, margin_x + 2, "Assertion Summary:", box_w - 4, curses.A_BOLD | curses.color_pair(_PAIR_BY_NAME.get("green", 0)))
        y += 2
        
        # Show all input data
        for key, val in state.assertion_input_data.items():
            if y >= top + box_h - 4:
                break
            line = f"  {key}: {val}"
            stdscr.addnstr(y, margin_x + 4, _truncate(line, box_w - 6), box_w - 6)
            y += 1
        
        y += 2
        confirm_line = "Type 'confirm' to create assertion or 'cancel' to abort"
        stdscr.addnstr(y, margin_x + 2, _truncate(confirm_line, box_w - 4), box_w - 4, curses.A_BOLD)
    except curses.error:
        pass


def _handle_assertion_wizard_command(state: AppState, cmdline: str) -> Tuple[str, bool]:
    """Handle commands within assertion wizard. Returns (message, exit_wizard)."""
    toks = cmdline.split()
    if not toks:
        return "", False
    
    cmd = toks[0].lower()
    args = toks[1:]
    
    if cmd == 'cancel':
        # Exit wizard
        state.assertion_wizard_active = False
        state.assertion_wizard_stage = ""
        state.assertion_selected_type = None
        state.assertion_input_data.clear()
        return "Assertion creation cancelled", True
    
    if state.assertion_wizard_stage == 'select_type':
        # User selects a number
        if cmd.isdigit():
            idx = int(cmd) - 1
            plugins = _get_assertion_plugins_info()
            if 0 <= idx < len(plugins):
                selected = plugins[idx]
                state.assertion_selected_type = selected['name']
                state.assertion_wizard_stage = 'input_data'
                state.assertion_input_data.clear()
                return f"Selected: {selected['name']}. Now enter field values.", False
            else:
                return f"Invalid selection. Choose 1-{len(plugins)}", False
        return "Enter a number to select assertion type", False
    
    elif state.assertion_wizard_stage == 'input_data':
        if cmd == 'set' and len(args) >= 2:
            field_num_str = args[0]
            value = ' '.join(args[1:])
            
            if field_num_str.isdigit():
                field_idx = int(field_num_str) - 1
                plugins = _get_assertion_plugins_info()
                plugin = next((p for p in plugins if p['name'] == state.assertion_selected_type), None)
                if plugin and 0 <= field_idx < len(plugin['fields']):
                    field = plugin['fields'][field_idx]
                    state.assertion_input_data[field['name']] = value
                    return f"Set {field['name']} = {value}", False
                else:
                    return f"Invalid field number", False
            else:
                return "Usage: set <field_number> <value>", False
        
        elif cmd == 'done':
            # Check if all required fields are filled
            plugins = _get_assertion_plugins_info()
            plugin = next((p for p in plugins if p['name'] == state.assertion_selected_type), None)
            if plugin:
                missing = []
                for field in plugin['fields']:
                    if field['name'] not in state.assertion_input_data or not state.assertion_input_data[field['name']]:
                        # Allow empty for optional fields (reset_signal, etc.)
                        if 'reset' in field['name'].lower() or field['prompt'].endswith('(or leave empty)'):
                            continue
                        missing.append(field['prompt'])
                
                if missing:
                    return f"Missing required fields: {', '.join(missing)}", False
                
                state.assertion_wizard_stage = 'confirm'
                return "Review your assertion. Type 'confirm' to create.", False
            return "Plugin not found", False
        
        return "Usage: set <field_num> <value> | 'done' to finish", False
    
    elif state.assertion_wizard_stage == 'confirm':
        if cmd == 'confirm':
            # Create the assertion
            result = _create_assertion_from_wizard(state)
            state.assertion_wizard_active = False
            state.assertion_wizard_stage = ""
            state.assertion_selected_type = None
            state.assertion_input_data.clear()
            return result, True
        return "Type 'confirm' to create or 'cancel' to abort", False
    
    return "", False


def _create_assertion_from_wizard(state: AppState) -> str:
    """Create assertion entry and write to Excel."""
    plugin_name = state.assertion_selected_type
    data = state.assertion_input_data
    
    # Build assertion description
    if plugin_name == 'counter':
        desc = f"Counter {data.get('counter_name', '')} increments on {data.get('increment_condition', '')}"
    elif plugin_name == 'handshake':
        desc = f"{data.get('phase_type', '')} handshake between {data.get('sender_signal', '')} and {data.get('receiver_signal', '')}"
    else:
        desc = f"{plugin_name} assertion"
    
    # Extract signals
    signals = []
    for key, val in data.items():
        if 'signal' in key.lower() or 'clock' in key.lower():
            if val:
                signals.append(val)
    
    # Add to state
    assertion_entry = {
        'type': plugin_name,
        'signals': signals,
        'description': desc,
        'data': dict(data),
    }
    state.assertions.append(assertion_entry)
    
    # Write to Excel
    try:
        excel_path = state.session_excel_path or state.excel_path
        if not excel_path or not Path(excel_path).exists():
            return f"✓ Assertion created in memory, but Excel not found for writing"
        
        _write_assertion_to_excel(excel_path, plugin_name, data)
        return f"✓ {plugin_name.upper()} assertion created and written to Excel!"
    except Exception as e:
        return f"✓ Assertion created in memory, but failed to write to Excel: {e}"


def _write_assertion_to_excel(excel_path: Path, plugin_name: str, data: Dict[str, Any]) -> None:
    """Write assertion data to corresponding Excel sheet."""
    try:
        from openpyxl import load_workbook  # type: ignore
        wb = load_workbook(str(excel_path))
        
        # Get plugin info to find sheet name
        plugins = _get_assertion_plugins_info()
        plugin = next((p for p in plugins if p['name'] == plugin_name), None)
        if not plugin:
            raise ValueError(f"Plugin {plugin_name} not found")
        
        sheet_name = plugin['sheet_name']
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found in Excel")
        
        ws = wb[sheet_name]
        
        # Find next empty row (simple approach: find first row after header with empty first cell)
        # This is plugin-specific logic - for now, append at the end
        max_row = ws.max_row
        next_row = max_row + 1
        
        # Write data based on plugin type
        if plugin_name == 'counter':
            # Counter sheet has specific structure - this is simplified
            # In practice, you'd parse the exact column layout
            ws.cell(row=next_row, column=1, value=data.get('counter_name', ''))
            ws.cell(row=next_row, column=2, value=data.get('clock_edge', ''))
            ws.cell(row=next_row, column=3, value=data.get('clock_signal', ''))
            ws.cell(row=next_row, column=4, value=data.get('reset_edge', ''))
            ws.cell(row=next_row, column=5, value=data.get('reset_signal', ''))
        
        elif plugin_name == 'handshake':
            # Handshake sheet structure
            ws.cell(row=next_row, column=1, value=data.get('phase_type', ''))
            ws.cell(row=next_row, column=2, value=data.get('sender_signal', ''))
            ws.cell(row=next_row, column=3, value=data.get('receiver_signal', ''))
        
        wb.save(str(excel_path))
        wb.close()
    except Exception as e:
        raise RuntimeError(f"Failed to write to Excel: {e}")


# ---------------------- Onboarding Wizard ----------------------------------

def _render_onboarding(stdscr: "curses._CursesWindow", state: AppState) -> None:
    max_y, max_x = stdscr.getmaxyx()
    title = "First Run - Guided Setup"
    try:
        stdscr.addnstr(0, 2, title, max_x - 4, curses.A_BOLD)
    except curses.error:
        pass
    # Box below title, with margins and safe height
    margin_x = 2
    top = 2
    reserved_bottom = 14  # space for candidates strip (up to 10) + hint + prompt
    box_h = max(6, max_y - top - reserved_bottom)
    box_w = max(20, max_x - (margin_x * 2))
    # Compact the box to avoid large empty area and overlap
    stage = (state.onboarding_stage or "").lower()
    if stage == 'rtl':
        box_h = min(box_h, 8)
    elif stage == 'module':
        box_h = min(box_h, 12)
    elif stage == 'excel':
        box_h = min(box_h, 13)  # Increased by 3 lines for better readability
    if top + box_h > max_y:
        box_h = max(6, max_y - top - 1)
    _draw_ascii_box(stdscr, top, margin_x, box_h, box_w)
    # No extra subtitle for a more professional look; rely on clear step guides below
    # Stage-specific content
    if state.onboarding_stage == 'rtl':
        lines = [
            "Step 1/3 — RTL Root",
            "- Enter file (.v/.sv) to pick modules in that file only.",
            "- Enter folder to scan all modules under it (recursive).",
            "- Tab: show candidates + extend common prefix. Use '/'.",
            "- Esc: cancel. prev/back: previous (exit).",
        ]
        for i, t in enumerate(lines):
            try:
                stdscr.addnstr(top + 2 + i, margin_x + 2, _truncate(t, box_w - 4), box_w - 4)
            except curses.error:
                pass
        # Candidates are rendered in a reserved strip near the bottom; do not draw here
    elif state.onboarding_stage == 'module':
        # Expand box to use available height except candidates/hint/prompt area
        box_h = max(8, max_y - top - 10)
        _draw_ascii_box(stdscr, top, margin_x, box_h, box_w)
        content_bottom = top + box_h - 2  # last drawable row inside the box
        try:
            stdscr.addnstr(min(top + 2, content_bottom), margin_x + 2, "Step 2/3 — Module: number+Enter. f <text> filter, F clear, n/N page (wrap), prev/back.", box_w - 4, curses.A_BOLD)
        except curses.error:
            pass
        # Render filtered, paginated module list in 3 columns
        mods = state.onboarding_modules
        if state.onboarding_filter:
            mods = [m for m in mods if state.onboarding_filter.lower() in m.lower()]
        page = max(0, state.onboarding_page)
        inner_h = max(1, content_bottom - (top + 4) + 1)
        inner_w = box_w - 4
        cols = 3
        col_w = max(10, inner_w // cols)
        rows = max(1, inner_h)
        items_per_page = rows * cols
        total = len(mods)
        start = (page * items_per_page) % max(1, ((total + items_per_page - 1) // items_per_page) * items_per_page)
        slice_mods = mods[start:start + items_per_page]
        # Grid render with clamping
        for i, m in enumerate(slice_mods):
            r = i % rows
            c = i // rows
            y = top + 4 + r
            if y > content_bottom:
                break
            x = margin_x + 2 + c * col_w
            label = f"[{start + i + 1}] {m}"
            try:
                stdscr.addnstr(y, x, _truncate(label, col_w - 2), col_w - 2)
            except curses.error:
                pass
        # Footer with page info (wrap-aware)
        try:
            pages = max(1, (total + items_per_page - 1) // items_per_page)
            stdscr.addnstr(content_bottom, margin_x + 2, _truncate(f"Page {page % pages + 1}/{pages}  Total: {total}", inner_w), inner_w, curses.A_DIM)
        except curses.error:
            pass
    elif state.onboarding_stage == 'excel':
        title = "Step 3/3 — Excel"
        found = state.onboarding_excel_autofound or state.excel_path
        try:
            stdscr.addnstr(top + 2, margin_x + 2, _truncate(title, box_w - 4), box_w - 4, curses.A_BOLD)
            content_bottom = top + box_h - 2
            y = top + 4
            
            if found:
                # Instruction lines
                if y <= content_bottom:
                    stdscr.addnstr(y, margin_x + 2, _truncate("Specify the path to the reference Excel file.", box_w - 4), box_w - 4)
                    y += 1
                
                if y <= content_bottom:
                    stdscr.addnstr(y, margin_x + 2, _truncate("Use '/' separator. Type 'prev' or 'back' to return to previous step.", box_w - 4), box_w - 4, curses.A_DIM)
                    y += 2  # Extra spacing before auto-detected section
                
                # Auto-detected file display with green highlight
                if y <= content_bottom:
                    stdscr.addnstr(y, margin_x + 2, _truncate("✓ Auto-detected:", box_w - 4), box_w - 4, curses.color_pair(_PAIR_BY_NAME.get("green", 0)) | curses.A_BOLD)
                    y += 1
                
                # Show the file path in green
                if y <= content_bottom:
                    file_display = f"  {str(found)}"
                    stdscr.addnstr(y, margin_x + 2, _truncate(file_display, box_w - 4), box_w - 4, curses.color_pair(_PAIR_BY_NAME.get("green", 0)))
                    y += 2  # Extra spacing
                
                # Confirmation prompt with color emphasis
                if y <= content_bottom:
                    prompt_msg = "Press Enter to accept"
                    stdscr.addnstr(y, margin_x + 2, _truncate(prompt_msg, box_w - 4), box_w - 4, curses.A_BOLD)
                    y += 1
                
                if y <= content_bottom:
                    or_msg = "or type a custom path below."
                    stdscr.addnstr(y, margin_x + 2, _truncate(or_msg, box_w - 4), box_w - 4, curses.A_DIM)
            else:
                # No auto-detected file
                if y <= content_bottom:
                    stdscr.addnstr(y, margin_x + 2, _truncate("Type the path to your Excel file and press Enter.", box_w - 4), box_w - 4)
                    y += 2
                
                if y <= content_bottom:
                    stdscr.addnstr(y, margin_x + 2, _truncate("No Excel found in Data/ folder.", box_w - 4), box_w - 4, curses.color_pair(_PAIR_BY_NAME.get("red", 0)) | curses.A_BOLD)
        except curses.error:
            pass


def _handle_onboarding_input(stdscr: "curses._CursesWindow", state: AppState, ch: int) -> bool:
    # Returns True if handled
    if state.onboarding_stage == 'rtl':
        if ch == 9:
            # Use existing completion on input line; nothing else to do
            return True
        if ch in (10, 13):
            # Accept current input line as rtl path
            # Read from prompt line content via main buffer; here we just move to next stage if set by main handler
            if state.rtl_start and Path(state.rtl_start).exists():
                # Build modules for next stage
                try:
                    mods_ctx, _mi, _occs = build_context_from_rtl(Path(state.rtl_start), None)
                    mods = sorted(list(mods_ctx.keys()))
                    state.onboarding_modules = mods
                except Exception:
                    state.onboarding_modules = []
                state.onboarding_stage = 'module'
            return True
        return False
    if state.onboarding_stage == 'module':
        if ch in (ord('n'), ord('N')):
            # wrap page advance/back based on last rendered geometry
            total = len(state.onboarding_modules)
            # Recompute items per page similar to renderer (uses 3 cols)
            # We don't have box_h here; approximate from screen height
            max_y, max_x = stdscr.getmaxyx()
            inner_h = max(8, max_y - 10) - 6
            cols = 3
            items_per_page = max(1, inner_h) * cols
            pages = max(1, (total + items_per_page - 1) // items_per_page)
            cur = state.onboarding_page % pages
            if ch == ord('n'):
                cur = (cur + 1) % pages
            else:
                cur = (cur - 1) % pages
            state.onboarding_page = cur
            return True
        # Filtering with 'f <substr>' handled in command parser; here we just refresh
        if ch in (10, 13):
            # Expect the user to type: pick <module> or set module <name>
            if state.target_module:
                state.onboarding_stage = 'excel'
            return True
        return False
    if state.onboarding_stage == 'excel':
        if ch in (10, 13):
            # Accept excel path; if empty and autofound exists, take autofound
            if not state.excel_path and state.onboarding_excel_autofound:
                state.excel_path = state.onboarding_excel_autofound
            if state.excel_path and Path(state.excel_path).exists():
                # Finish onboarding
                state.onboarding_active = False
                state.onboarding_stage = None
                # Persist session snapshot immediately
                _save_session_snapshot(state)
            return True
        return False
    return False


if __name__ == "__main__":
    run()



