from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

from openpyxl import load_workbook

from .base import BaseAssertionPlugin
from .registry import register


# 유틸: 값이 들어있는 셀 찾기(대소문자 무시)
def _find_cell(ws, value: str) -> Tuple[Optional[int], Optional[int]]:
    tgt = (value or "").strip().lower()
    for row in ws.iter_rows():
        for c in row:
            v = c.value
            if v is None:
                continue
            if str(v).strip().lower() == tgt:
                return c.row, c.column
    return None, None

def _get_sheet_ci(wb, want_name: str):
    target = (want_name or "").strip().lower()
    for nm in wb.sheetnames:
        if str(nm).strip().lower() == target:
            return wb[nm]
    raise KeyError(f"Worksheet {want_name} does not exist.")


# 프롬프트 유틸: 하나 선택(커스텀 허용)
def _pick_one(title: str, options: List[Tuple[str, str]], allow_custom: bool = False) -> str:
    print(title, flush=True)
    for i, (label, _) in enumerate(options, start=1):
        print(f"  [{i}] {label}")
    if allow_custom:
        print("  [0] Enter custom")
    while True:
        try:
            s = input("Select > ").strip()
        except EOFError:
            return options[0][1] if options else ""
        if allow_custom and s == "0":
            try:
                return input("Enter value > ").strip()
            except EOFError:
                return ""
        if s.isdigit():
            i = int(s)
            if 1 <= i <= len(options):
                return options[i - 1][1]
        print("Invalid selection. Try again.", flush=True)


# 세션 디렉터리에서 module_define.json → assertion_inputs.json 우선 읽기
def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_module_define(xls_path: Path) -> Dict[str, Any]:
    session_dir = xls_path.parent
    md = _read_json(session_dir / "module_define.json")
    if md:
        return md
    ai = _read_json(session_dir / "assertion_inputs.json")
    if ai:
        return {
            "module": ai.get("module") or "",
            "clocks": ai.get("clocks") or [],
            "resets": ai.get("resets") or [],
            "inputs": ai.get("inputs") or [],
            "outputs": ai.get("outputs") or [],
            "inouts": ai.get("inouts") or [],
            "parameters": ai.get("parameters") or [],
        }
    return {}


# Base Clock/Reset 자동 추정(없으면 inputs에서 패턴으로 픽)
def _auto_pick_clk_rst(module_info: Dict[str, Any]) -> Tuple[str, str]:
    clk = ""
    rst = ""
    for c in (module_info.get("clocks") or []):
        n = c.get("name") or ""
        if n:
            clk = n
            break
    for r in (module_info.get("resets") or []):
        n = r.get("name") or ""
        if n:
            rst = n
            break
    if not clk:
        for it in module_info.get("inputs") or []:
            n = (it.get("name") or "").lower()
            if "clk" in n or n.endswith("clock"):
                clk = it.get("name") or ""
                break
    if not rst:
        for it in module_info.get("inputs") or []:
            n = (it.get("name") or "").lower()
            if "rst" in n or "reset" in n:
                rst = it.get("name") or ""
                break
    return clk, rst


# Define 시트를 간략히 채움(없으면 생성)
def _ensure_define_sheet_and_fill(wb, module_info: Dict[str, Any]) -> None:
    def_ws = None
    for nm in wb.sheetnames:
        if str(nm).strip().lower() == "define":
            def_ws = wb[nm]
            break
    if def_ws is None:
        def_ws = wb.create_sheet(title="Define")
    # 간단 레이아웃: 라벨과 이름들 나열
    def_ws.cell(row=1, column=1, value="Module")
    def_ws.cell(row=1, column=2, value=(module_info.get("module") or ""))
    row = 3
    def _dump(label: str, items: List[Dict[str, Any]]):
        nonlocal row
        def_ws.cell(row=row, column=1, value=label)
        names = [it.get("name") for it in (items or []) if it.get("name")]
        if not names:
            row += 1
            return
        for i, n in enumerate(names, start=0):
            def_ws.cell(row=row + i, column=2, value=n)
        row += max(1, len(names)) + 1
    _dump("Parameters", module_info.get("parameters") or [])
    _dump("Inputs",     module_info.get("inputs")     or [])
    _dump("Outputs",    module_info.get("outputs")    or [])
    _dump("Inouts",     module_info.get("inouts")     or [])
    _dump("Clocks",     module_info.get("clocks")     or [])
    _dump("Resets",     module_info.get("resets")     or [])


# PulseWidth 시트에 한 행 기록하고 행번호 반환
def _update_pulsewidth_sheet(ws, cfg: Dict[str, Any], module_info: Dict[str, Any]) -> int:
    # 표가 없으면 생성
    try:
        h_row, cols, data_start = _locate_pw_table(ws)
    except RuntimeError:
        _ensure_pw_table(ws)
        h_row, cols, data_start = _locate_pw_table(ws)
    # 기록할 행: Type == "hpulse"가 이미 있으면 그 행을 덮어씀. 없으면 첫 데이터 행.
    wanted_type = (cfg.get("Type") or "hpulse")
    found_row = _find_type_row(ws, cols, data_start, wanted_type)
    write_row = found_row if found_row is not None else data_start

    ws.cell(row=write_row, column=cols["Type"],               value=cfg.get("Type", "hpulse"))
    ws.cell(row=write_row, column=cols["Count_Trigger"],      value=(cfg.get("Count_Trigger") or ""))
    ws.cell(row=write_row, column=cols["Target_Pulse"],       value=(cfg.get("Target_Pulse") or ""))
    ws.cell(row=write_row, column=cols["Expected_Min_Value"], value=(cfg.get("Expected_Min_Value") or ""))
    ws.cell(row=write_row, column=cols["Expected_Max_Value"], value=(cfg.get("Expected_Max_Value") or ""))

    # Base Clock/Reset 라벨 및 값(비어있을 때만 자동 채움)
    clk_r, clk_c = _find_cell(ws, "Base Clock")
    rst_r, rst_c = _find_cell(ws, "Base Reset")
    if clk_r is None:
        clk_r, clk_c = h_row + 3, 1
        ws.cell(row=clk_r, column=clk_c, value="Base Clock")
    if rst_r is None:
        rst_r, rst_c = h_row + 4, 1
        ws.cell(row=rst_r, column=rst_c, value="Base Reset")
    cur_clk = ws.cell(row=clk_r, column=clk_c + 1).value
    cur_rst = ws.cell(row=rst_r, column=rst_c + 1).value
    clk_name, rst_name = _auto_pick_clk_rst(module_info)
    if clk_name and (cur_clk is None or str(cur_clk).strip() == ""):
        ws.cell(row=clk_r, column=clk_c + 1, value=clk_name)
    if rst_name and (cur_rst is None or str(cur_rst).strip() == ""):
        ws.cell(row=rst_r, column=rst_c + 1, value=rst_name)
    # hpulse일 때만 Count_Trigger를 Base Clock 값으로 덮어쓴다
    if (cfg.get("Type") or "").strip().lower() == "hpulse":
        base_clk_val = ws.cell(row=clk_r, column=clk_c + 1).value
        ws.cell(row=write_row, column=cols["Count_Trigger"], value=(str(base_clk_val).strip() if base_clk_val else ""))

    return write_row


# 모듈 I/O를 옵션으로 만들어주는 헬퍼
def _signal_options(module_info: Dict[str, Any]) -> List[Tuple[str, str]]:
    in_names  = [(f"in : {p.get('name')}",  p.get("name") or "") for p in (module_info.get("inputs")  or []) if p.get("name")]
    out_names = [(f"out: {p.get('name')}",  p.get("name") or "") for p in (module_info.get("outputs") or []) if p.get("name")]
    return in_names + out_names


# Pulse Width 헤더/컬럼 인덱스 추출
def _locate_pw_table(ws) -> Tuple[int, Dict[str, int], int]:
    """
    returns:
      header_row, cols_map, data_start_row
    cols_map keys: 'Type','Count_Trigger','Target_Pulse','Expected_Min_Value','Expected_Max_Value'
    """
    h_row, h_col = _find_cell(ws, "Pulse Width")
    if h_row is None:
        raise RuntimeError("PulseWidth: 'Pulse Width' 헤더를 찾지 못했습니다.")
    labels_row = h_row + 1

    # 레이블 매칭(공백/밑줄/대소문자 무시)
    want_labels = ["Type", "Count_Trigger", "Target_Pulse", "Expected_Min_Value", "Expected_Max_Value"]

    def norm(s: Any) -> str:
        return "".join(ch for ch in str(s).strip().lower().replace(" ", "_") if ch != "\u200b")  # zero-width 제거

    cols: Dict[str, int] = {}
    # labels_row 전체를 훑으며 각 레이블의 컬럼을 찾는다.
    for c in range(1, ws.max_column + 1):
        val = ws.cell(row=labels_row, column=c).value
        if val is None:
            continue
        n = norm(val)
        for w in want_labels:
            if n == norm(w):
                cols[w] = c

    # 누락 허용 X: 명시된 다섯 컬럼 모두 필요
    missing = [w for w in want_labels if w not in cols]
    if missing:
        raise RuntimeError(f"PulseWidth: 부족한 컬럼 라벨: {', '.join(missing)} (헤더 아래 행에서 탐색)")

    data_start = labels_row + 1
    return h_row, cols, data_start

def _find_type_row(ws, cols: Dict[str, int], data_start: int, type_val: str) -> Optional[int]:
    """Type 컬럼에서 주어진 값과 일치하는(대소문자/공백 무시) 첫 행을 찾는다."""
    want = (type_val or "").strip().lower()
    r = data_start
    while r <= (ws.max_row or data_start):
        cell_v = ws.cell(row=r, column=cols["Type"]).value
        if cell_v is None or str(cell_v).strip() == "":
            break
        if str(cell_v).strip().lower() == want:
            return r
        r += 1
    return None


def _read_base_clk_rst(ws) -> Tuple[str, str]:
    clk_r, clk_c = _find_cell(ws, "Base Clock")
    rst_r, rst_c = _find_cell(ws, "Base Reset")
    clk = ws.cell(row=clk_r, column=clk_c + 1).value if clk_r else None
    rst = ws.cell(row=rst_r, column=rst_c + 1).value if rst_r else None
    return (str(clk).strip() if clk else ""), (str(rst).strip() if rst else "")


def _iter_rows(ws, cols: Dict[str, int], data_start: int):
    r = data_start
    while r <= (ws.max_row or data_start):
        t = ws.cell(row=r, column=cols["Type"]).value
        # Type이 비어있으면 그 이후는 비어있다고 간주하고 종료
        if t is None or str(t).strip() == "":
            break
        row = {k: ws.cell(row=r, column=cols[k]).value for k in cols.keys()}
        yield r, row
        r += 1

def _collect_available_types(ws) -> List[str]:
    """Pulse Width 표에서 존재하는 Type 값을 수집한다. 없으면 기본 리스트를 반환."""
    try:
        _, cols, data_start = _locate_pw_table(ws)
    except Exception:
        return ["hpulse", "vpulse"]
    types: List[str] = []
    for _, row in _iter_rows(ws, cols, data_start):
        t = str(row.get("Type") or "").strip().lower()
        if t and t not in types:
            types.append(t)
    return types or ["hpulse", "vpulse"]


# -------- Bit-width helpers (DUT ports) --------
def _normalize_range_token(token: Any) -> str:
    """Normalize to [msb:lsb]; default to [0:0] for 1-bit/unknown."""
    if token is None:
        return "[0:0]"
    t = str(token).strip().replace(" ", "")
    if not t:
        return "[0:0]"
    if t.startswith("[") and t.endswith("]"):
        return t
    try:
        n = int(t, 10)
        return f"[{n-1}:0]" if n >= 1 else "[0:0]"
    except Exception:
        return "[0:0]"

def _port_width_token(mod: Dict[str, Any], name: str) -> str:
    """Find port by name and return width token '[msb:lsb]' (defaults [0:0])."""
    if not name or not mod:
        return "[0:0]"
    want = (name or "").strip()
    candidates = [
        mod.get("ports") or [],
        mod.get("inputs") or [],
        mod.get("outputs") or [],
        mod.get("inouts") or [],
        mod.get("clocks") or [],
        mod.get("resets") or [],
    ]
    for arr in candidates:
        for it in arr:
            if (it.get("name") or "") != want:
                continue
            # packed forms first
            for key in ("packed_range", "range", "packed", "decl"):
                pr = it.get(key)
                if pr is not None and str(pr).strip():
                    return _normalize_range_token(pr)
            # width as integer/string
            for key in ("width", "bit_width", "width_bits"):
                w = it.get(key)
                if w is not None and str(w).strip():
                    return _normalize_range_token(str(w))
            # separate ends
            for lk, rk in (("msb", "lsb"), ("left", "right")):
                msb = it.get(lk); lsb = it.get(rk)
                if msb is not None and lsb is not None:
                    try:
                        return f"[{int(msb)}:{int(lsb)}]"
                    except Exception:
                        return f"[{msb}:{lsb}]"
            return "[0:0]"
    return "[0:0]"

def _fmt_input_decl(sig: str, width_tok: str) -> str:
    """Format 'input logic [msb:lsb] name' (width defaults to [0:0])."""
    tok = (width_tok or "").strip() or "[0:0]"
    return f"input logic {tok} {sig}"


def _sv_header() -> str:
    return '`include "uvm_macros.svh"\nimport uvm_pkg::*;\n\n'


def _build_hpulse_sv(base_clk: str, base_rst: str, target_pulse: str,
                     expected_min: str, expected_max: str,
                     w_clk: str, w_rst: str, w_tp: str, w_min: str, w_max: str) -> str:
    # 요청 포맷을 최대한 준수하며 SV 문법 오류는 보정
    lines: List[str] = []
    lines.append(_sv_header())
    lines.append("module assertion_hpulse")
    lines.append("(")
    lines.append(f"    {_fmt_input_decl(base_clk,     w_clk)},")
    lines.append(f"    {_fmt_input_decl(base_rst,     w_rst)},")
    lines.append(f"    {_fmt_input_decl(target_pulse, w_tp)},")
    lines.append(f"    {_fmt_input_decl(expected_min, w_min)},")
    lines.append(f"    {_fmt_input_decl(expected_max, w_max)}")
    lines.append(");")
    lines.append("")
    lines.append("property p_hpulse(target_pulse, expected_min_value, expected_max_value);")
    lines.append("    int value_count;")
    lines.append(f"    @(posedge {base_clk}) disable iff(!{base_rst})")
    lines.append("    (target_pulse) |-> (1, value_count = 0)")
    lines.append("    ##1 (target_pulse, value_count = value_count + 1)[*0:$]")
    lines.append("    ##1 (!target_pulse, value_count = value_count + 1)")
    lines.append("    ##0 (expected_min_value <= value_count && value_count <= expected_max_value);")
    lines.append("endproperty")
    lines.append("")
    lines.append(f'assert property (p_hpulse({target_pulse}, {expected_min}, {expected_max}))')
    lines.append('    else $error("failed at %t", $time);')
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)


def _build_hpulse_inst_sv(base_clk: str, base_rst: str, target_pulse: str,
                          expected_min: str, expected_max: str) -> str:
    lines: List[str] = []
    lines.append(_sv_header())
    lines.append("assertion_hpulse")
    lines.append(" u_assertion_hpulse ();")
    lines.append("")
    lines.append(f"assign u_assertion_hpulse.{base_clk} = top.dut.{base_clk};")
    lines.append(f"assign u_assertion_hpulse.{base_rst} = top.dut.{base_rst};")
    lines.append(f"assign u_assertion_hpulse.{target_pulse} = top.dut.{target_pulse};")
    lines.append(f"assign u_assertion_hpulse.{expected_min} = top.dut.{expected_min};")
    lines.append(f"assign u_assertion_hpulse.{expected_max} = top.dut.{expected_max};")
    lines.append("")
    return "\n".join(lines)


def _build_vpulse_sv(base_clk: str, base_rst: str, count_trig: str,
                     target_pulse: str, expected_min: str, expected_max: str,
                     w_clk: str, w_rst: str, w_ct: str, w_tp: str, w_min: str, w_max: str) -> str:
    lines: List[str] = []
    lines.append(_sv_header())
    lines.append("module assertion_vpulse")
    lines.append("(")
    lines.append(f"    {_fmt_input_decl(base_clk,     w_clk)},")
    lines.append(f"    {_fmt_input_decl(base_rst,     w_rst)},")
    lines.append(f"    {_fmt_input_decl(count_trig,   w_ct)},")
    lines.append(f"    {_fmt_input_decl(target_pulse, w_tp)},")
    lines.append(f"    {_fmt_input_decl(expected_min, w_min)},")
    lines.append(f"    {_fmt_input_decl(expected_max, w_max)}")
    lines.append(");")
    lines.append("")
    # sequence: Count_Trigger의 네거티브 엣지에서 target_pulse 길이를 카운트
    lines.append("sequence s_vpulse(value_count);")
    lines.append(f"    @(negedge {count_trig})")
    lines.append(f"    ({target_pulse}, value_count = value_count + 1)[*0:$]")
    lines.append(f"    ##1 (!{target_pulse});")
    lines.append("endsequence")
    lines.append("")
    lines.append("property p_vpulse(count_trigger, target_pulse, expected_min_value, expected_max_value);")
    lines.append("    int value_count;")
    lines.append(f"    @(posedge {base_clk}) disable iff(!{base_rst})")
    lines.append("    (target_pulse) |-> (1, value_count = 0)")
    lines.append("    ##0 s_vpulse(value_count)")
    lines.append("    ##1 (expected_min_value <= value_count && value_count <= expected_max_value);")
    lines.append("endproperty")
    lines.append("")
    lines.append(f'assert property (p_vpulse({count_trig}, {target_pulse}, {expected_min}, {expected_max}))')
    lines.append('    else $error("failed at %t", $time);')
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)


def _build_vpulse_inst_sv(base_clk: str, base_rst: str, count_trig: str,
                          target_pulse: str, expected_min: str, expected_max: str) -> str:
    lines: List[str] = []
    lines.append(_sv_header())
    lines.append("assertion_vpulse")
    lines.append(" u_assertion_vpulse ();")
    lines.append("")
    lines.append(f"assign u_assertion_vpulse.{base_clk} = top.dut.{base_clk};")
    lines.append(f"assign u_assertion_vpulse.{base_rst} = top.dut.{base_rst};")
    lines.append(f"assign u_assertion_vpulse.{count_trig} = top.dut.{count_trig};")
    lines.append(f"assign u_assertion_vpulse.{target_pulse} = top.dut.{target_pulse};")
    lines.append(f"assign u_assertion_vpulse.{expected_min} = top.dut.{expected_min};")
    lines.append(f"assign u_assertion_vpulse.{expected_max} = top.dut.{expected_max};")
    lines.append("")
    return "\n".join(lines)


def _ensure_define_base_clk_rst(wb, module_info: Dict[str, Any]) -> None:
    """
    Define 탭의 'Base Clock' / 'Base Reset' 라벨 우측 셀에 모듈 파싱 결과를 기록.
    라벨이 없으면 생성한다.
    """
    try:
        ws = _get_sheet_ci(wb, "Define")
    except KeyError:
        ws = wb.create_sheet(title="Define")

    # 라벨 위치 확보
    clk_r, clk_c = _find_cell(ws, "Base Clock")
    rst_r, rst_c = _find_cell(ws, "Base Reset")
    if clk_r is None:
        clk_r, clk_c = 2, 1
        ws.cell(row=clk_r, column=clk_c, value="Base Clock")
    if rst_r is None:
        rst_r, rst_c = 3, 1
        ws.cell(row=rst_r, column=rst_c, value="Base Reset")

    # 값 기록(비어있으면 덮어씀)
    clk_name, rst_name = _auto_pick_clk_rst(module_info)
    cur_clk = ws.cell(row=clk_r, column=clk_c + 1).value
    cur_rst = ws.cell(row=rst_r, column=rst_c + 1).value
    if clk_name and (cur_clk is None or str(cur_clk).strip() == ""):
        ws.cell(row=clk_r, column=clk_c + 1, value=clk_name)
    if rst_name and (cur_rst is None or str(cur_rst).strip() == ""):
        ws.cell(row=rst_r, column=rst_c + 1, value=rst_name)


def _ensure_pw_table(ws) -> None:
    """
    Pulse Width 헤더/라벨이 없으면 기본 형태로 생성한다.
    헤더: (row=1,col=1) "Pulse Width"
    라벨: 그 바로 아래 행에 5개 컬럼 라벨 생성
    """
    h_row, h_col = _find_cell(ws, "Pulse Width")
    if h_row is None:
        h_row, h_col = 1, 1
        ws.cell(row=1, column=1, value="Pulse Width")
    labels = ["Type", "Count_Trigger", "Target_Pulse", "Expected_Min_Value", "Expected_Max_Value"]
    labels_row = h_row + 1
    for i, lab in enumerate(labels):
        if not ws.cell(row=labels_row, column=h_col + i).value:
            ws.cell(row=labels_row, column=h_col + i, value=lab)


@register
class PulseWidthPlugin(BaseAssertionPlugin):
    plugin_name = "pulseWidth"
    sheet_name = "PulseWidth"

    def parse(self, xls_path: Path) -> Dict[str, Any]:
        # 0) 모듈 정보 로드
        module_info = _load_module_define(Path(xls_path))

        # 0.5) 타입 선택(핸드셰이크 방식): 시트에 존재하는 Type 목록을 우선 사용, 없으면 기본 값
        try:
            wb_ro = load_workbook(xls_path, data_only=True)
            ws_ro = _get_sheet_ci(wb_ro, self.sheet_name)
            avail_types = _collect_available_types(ws_ro)
        except Exception:
            avail_types = ["hpulse", "vpulse"]
        type_choice = _pick_one("Select PulseWidth type", [(t, t) for t in avail_types])

        # 1) 사용자 입력 수집: 모듈 I/O 목록에서 고르거나 커스텀
        sig_opts = _signal_options(module_info) or [("manual input", "")]
        # hpulse 선택 시 Count_Trigger 질문 스킵, vpulse 선택 시에만 질문
        type_lc = (type_choice or "hpulse").strip().lower()
        if type_lc == "hpulse":
            count_trig = ""  # _update_pulsewidth_sheet에서 Base Clock 값으로 채워짐
        else:
            count_trig = _pick_one("Select Count_Trigger signal", sig_opts, allow_custom=True)
        target_pulse = _pick_one("Select Target_Pulse signal", sig_opts, allow_custom=True)
        exp_min = _pick_one("Select Expected_Min_Value signal/const", sig_opts, allow_custom=True)
        exp_max = _pick_one("Select Expected_Max_Value signal/const", sig_opts, allow_custom=True)
        cfg = {
            "Type": type_choice or "hpulse",
            "Count_Trigger": count_trig,
            "Target_Pulse": target_pulse,
            "Expected_Min_Value": exp_min,
            "Expected_Max_Value": exp_max,
        }

        # 2) 세션 엑셀을 열어 Define/PulseWidth 기록
        wb_w = load_workbook(xls_path)  # 쓰기용
        # Define 탭에 Base Clock/Reset 채우기
        if module_info:
            _ensure_define_base_clk_rst(wb_w, module_info)
        # PulseWidth 탭 가져오기(없으면 생성) 및 한 행 기록
        try:
            ws_w = _get_sheet_ci(wb_w, self.sheet_name)
        except KeyError:
            ws_w = wb_w.create_sheet(title=self.sheet_name)
        write_row = _update_pulsewidth_sheet(ws_w, cfg, module_info)
        wb_w.save(xls_path)

        # 3) data_only로 재오픈(값 위주 파싱), 방금 기록한 행만 파싱
        wb = load_workbook(xls_path, data_only=True)
        ws = _get_sheet_ci(wb, self.sheet_name)

        # 베이스 클럭/리셋
        base_clk, base_rst = _read_base_clk_rst(ws)
        # Define 탭 보강 로직 유지
        if not base_clk or not base_rst:
            try:
                def_ws = _get_sheet_ci(wb, "Define")
                dr, dc = _find_cell(def_ws, "Base Clock")
                rr, rc = _find_cell(def_ws, "Base Reset")
                if dr:
                    v = def_ws.cell(row=dr, column=dc + 1).value
                    base_clk = base_clk or (str(v).strip() if v else "")
                if rr:
                    v = def_ws.cell(row=rr, column=rc + 1).value
                    base_rst = base_rst or (str(v).strip() if v else "")
            except KeyError:
                pass
        if not base_clk or not base_rst:
            return {"blocks": []}

        # Pulse Width 테이블 파악 및 방금 행만 파싱
        _, cols, _ = _locate_pw_table(ws)
        row = {
            k: ws.cell(row=write_row, column=cols[k]).value
            for k in ["Type", "Count_Trigger", "Target_Pulse", "Expected_Min_Value", "Expected_Max_Value"]
        }
        t = str(row.get("Type") or "").strip().lower()
        blocks: List[Dict[str, Any]] = []
        if t == (type_choice or "hpulse").strip().lower():
            target_pulse = str(row.get("Target_Pulse") or "").strip()
            exp_min = str(row.get("Expected_Min_Value") or "").strip()
            exp_max = str(row.get("Expected_Max_Value") or "").strip()
            count_trig = str(row.get("Count_Trigger") or "").strip()
            # bit widths from DUT JSON (always default to [0:0])
            w_clk = _port_width_token(module_info, base_clk)
            w_rst = _port_width_token(module_info, base_rst)
            w_ct  = _port_width_token(module_info, count_trig) if t == "vpulse" and count_trig else "[0:0]"
            w_tp  = _port_width_token(module_info, target_pulse)
            w_min = _port_width_token(module_info, exp_min)
            w_max = _port_width_token(module_info, exp_max)
            blocks.append({
                "Type": t,
                "Base Clock": base_clk,   # PulseWidth 시트의 라벨 우측 값
                "Base Reset": base_rst,   # PulseWidth 시트의 라벨 우측 값
                "Target_Pulse": target_pulse,
                "Expected_Min_Value": exp_min,
                "Expected_Max_Value": exp_max,
                "Count_Trigger": count_trig,
                # widths
                "Base Clock Width": w_clk,
                "Base Reset Width": w_rst,
                "Target_Pulse Width": w_tp,
                "Expected_Min_Value Width": w_min,
                "Expected_Max_Value Width": w_max,
                "Count_Trigger Width": w_ct,
            })
        return {"blocks": blocks}

    def generate_sv(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        out_dir = Path(context.get("output_dir") or context.get("session_dir") or ".")
        out_dir.mkdir(parents=True, exist_ok=True)

        snippets: List[str] = []
        for b in (parsed.get("blocks") or []):
            t = (b.get("Type") or "").lower()
            base_clk = b.get("Base Clock", "")
            base_rst = b.get("Base Reset", "")
            target_pulse = b.get("Target_Pulse", "")
            exp_min = b.get("Expected_Min_Value", "")
            exp_max = b.get("Expected_Max_Value", "")
            # widths (defaults)
            w_clk = b.get("Base Clock Width", "[0:0]")
            w_rst = b.get("Base Reset Width", "[0:0]")
            w_tp  = b.get("Target_Pulse Width", "[0:0]")
            w_min = b.get("Expected_Min_Value Width", "[0:0]")
            w_max = b.get("Expected_Max_Value Width", "[0:0]")
            if t == "hpulse":
                if not base_clk or not base_rst or not target_pulse or not exp_min or not exp_max:
                    continue
                sv = _build_hpulse_sv(base_clk, base_rst, target_pulse, exp_min, exp_max,
                                      w_clk, w_rst, w_tp, w_min, w_max)
                inst_sv = _build_hpulse_inst_sv(base_clk, base_rst, target_pulse, exp_min, exp_max)
                (out_dir / "assertion_hpulse.sv").write_text(sv, encoding="utf-8")
                (out_dir / "assertion_hpulse_inst.sv").write_text(inst_sv, encoding="utf-8")
                snippets.append(sv)
            elif t == "vpulse":
                count_trig = b.get("Count_Trigger", "")
                w_ct = b.get("Count_Trigger Width", "[0:0]")
                if not base_clk or not base_rst or not count_trig or not target_pulse or not exp_min or not exp_max:
                    continue
                sv = _build_vpulse_sv(base_clk, base_rst, count_trig, target_pulse, exp_min, exp_max,
                                      w_clk, w_rst, w_ct, w_tp, w_min, w_max)
                inst_sv = _build_vpulse_inst_sv(base_clk, base_rst, count_trig, target_pulse, exp_min, exp_max)
                (out_dir / "assertion_vpulse.sv").write_text(sv, encoding="utf-8")
                (out_dir / "assertion_vpulse_inst.sv").write_text(inst_sv, encoding="utf-8")
                snippets.append(sv)

        return snippets

    def emit_json(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return parsed