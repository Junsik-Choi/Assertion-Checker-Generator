from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import json
from openpyxl import load_workbook

from .base import BaseAssertionPlugin
from .registry import register

# -----------------------------
# Local helpers (self-contained)
# -----------------------------
def _get_sheet_ci(wb, name: str, create: bool = True):
    tgt = name.strip().lower()
    for s in wb.sheetnames:
        if str(s).strip().lower() == tgt:
            return wb[s]
    if not create:
        raise KeyError(name)
    return wb.create_sheet(title=name)

def _find_cell(ws, key: str) -> Tuple[Optional[int], Optional[int]]:
    key_l = str(key).strip().lower()
    for r in range(1, (ws.max_row or 1) + 1):
        for c in range(1, (ws.max_column or 1) + 1):
            v = ws.cell(row=r, column=c).value
            if v is None:
                continue
            if str(v).strip().lower() == key_l:
                return r, c
    return None, None

def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _load_module_define(xls_path: Path) -> Dict[str, Any]:
    root = xls_path.parent
    md = _read_json(root / "module_define.json")
    if md:
        return md
    ai = _read_json(root / "assertion_inputs.json")
    if ai:
        return {
            "module": ai.get("module") or "",
            "clocks": ai.get("clocks") or [],
            "resets": ai.get("resets") or [],
            "inputs": ai.get("inputs") or [],
            "outputs": ai.get("outputs") or [],
            "inouts": ai.get("inouts") or [],
            "ports": ai.get("ports") or [],
        }
    return {}

def _signal_options(mod: Dict[str, Any]) -> List[Tuple[str, str]]:
    opts: List[Tuple[str, str]] = []
    for it in (mod.get("inputs") or []):
        n = it.get("name")
        if n:
            opts.append((n, n))
    # dedup
    seen, uniq = set(), []
    for label, val in opts:
        if val in seen:
            continue
        seen.add(val); uniq.append((label, val))
    return uniq

def _pick_one(question: str, options: List[Tuple[str, str]], allow_custom: bool = False) -> str:
    print(question)
    for i, (label, _) in enumerate(options, start=1):
        print(f"  [{i}] {label}")
    if allow_custom:
        print("  [0] Custom Value")
    while True:
        sel = input("> ").strip()
        if allow_custom and sel == "0":
            return input("Enter value: ").strip()
        if sel.isdigit():
            i = int(sel)
            if 1 <= i <= len(options):
                return options[i - 1][1]
        print("Invalid selection. Try again.")

def _normalize_range_token(token: Any) -> str:
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
    if not name or not mod:
        return "[0:0]"
    want = (name or "").strip()
    cands = [
        mod.get("ports") or [],
        mod.get("inputs") or [],
        mod.get("outputs") or [],
        mod.get("inouts") or [],
        mod.get("clocks") or [],
        mod.get("resets") or [],
    ]
    for arr in cands:
        for it in arr:
            if (it.get("name") or "") != want:
                continue
            for k in ("packed_range", "range", "packed", "decl"):
                pr = it.get(k)
                if pr is not None and str(pr).strip():
                    return _normalize_range_token(pr)
            for k in ("width", "bit_width", "width_bits"):
                w = it.get(k)
                if w is not None and str(w).strip():
                    return _normalize_range_token(str(w))
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
    tok = (width_tok or "").strip() or "[0:0]"
    return f"input logic {tok} {sig}"

def _ensure_define_base_clk_rst(wb, module_info: Dict[str, Any]) -> None:
    ws = None
    for nm in wb.sheetnames:
        if str(nm).strip().lower() == "define":
            ws = wb[nm]; break
    if ws is None:
        ws = wb.create_sheet(title="Define")
    clk_r, clk_c = _find_cell(ws, "Base Clock")
    rst_r, rst_c = _find_cell(ws, "Base Reset")
    if clk_r is None:
        clk_r, clk_c = 2, 1
        ws.cell(row=clk_r, column=clk_c, value="Base Clock")
    if rst_r is None:
        rst_r, rst_c = 3, 1
        ws.cell(row=rst_r, column=rst_c, value="Base Reset")
    # try auto-fill from module info
    clk = ""
    for it in (module_info.get("clocks") or []):
        n = it.get("name"); 
        if n: clk = n; break
    rst = ""
    for it in (module_info.get("resets") or []):
        n = it.get("name"); 
        if n: rst = n; break
    if clk and not (ws.cell(row=clk_r, column=clk_c + 1).value):
        ws.cell(row=clk_r, column=clk_c + 1, value=clk)
    if rst and not (ws.cell(row=rst_r, column=rst_c + 1).value):
        ws.cell(row=rst_r, column=rst_c + 1, value=rst)

def _read_base_clk_rst(ws) -> Tuple[str, str]:
    cr, cc = _find_cell(ws, "Base Clock")
    rr, rc = _find_cell(ws, "Base Reset")
    clk = ws.cell(row=cr, column=cc + 1).value if cr else ""
    rst = ws.cell(row=rr, column=rc + 1).value if rr else ""
    return (str(clk).strip() if clk else ""), (str(rst).strip() if rst else "")

# 수식/시트 참조를 실제 값으로 역참조
def _resolve_ref(wb, raw: Any) -> str:
    s = "" if raw is None else str(raw).strip()
    if not s:
        return ""
    expr = s[1:].strip() if s.startswith("=") else s
    if "!" not in expr:
        return s
    sheet_name, addr = expr.split("!", 1)
    sheet_name = sheet_name.strip().strip("'").strip('"')
    try:
        ws2 = wb[sheet_name]
        v = ws2[addr].value
        return str(v).strip() if v is not None else ""
    except Exception:
        return s

def _read_label_right_resolved(wb, ws, label: str) -> str:
    r, c = _find_cell(ws, label)
    if r is None:
        return ""
    raw = ws.cell(row=r, column=c + 1).value
    val = _resolve_ref(wb, raw)
    return val if val != "" else (str(raw).strip() if raw is not None else "")

def _read_label_below_resolved(wb, ws, label: str) -> str:
    r, c = _find_cell(ws, label)
    if r is None:
        return ""
    raw = ws.cell(row=r + 1, column=c).value
    val = _resolve_ref(wb, raw)
    return val if val != "" else (str(raw).strip() if raw is not None else "")

# 아래/우측 라벨 유틸(누락 보완)
def _read_label_below(ws, label: str) -> str:
    r, c = _find_cell(ws, label)
    if r is None:
        return ""
    v = ws.cell(row=r + 1, column=c).value
    return str(v).strip() if v is not None else ""

def _write_label_below(ws, label: str, value: str) -> None:
    r, c = _find_cell(ws, label)
    if r is None:
        # 시트 상단의 DelayCondition 헤더 기준으로 라벨 배치
        hdr_r, hdr_c = _find_cell(ws, "DelayCondition")
        if hdr_r is None:
            hdr_r, hdr_c = 1, 1
            ws.cell(row=hdr_r, column=hdr_c, value="DelayCondition")
        r, c = hdr_r + 1, hdr_c
        # 첫 빈 라벨 슬롯 찾기
        while ws.cell(row=r, column=c).value not in (None, ""):
            r += 1
        ws.cell(row=r, column=c, value=label)
    ws.cell(row=r + 1, column=c, value=value)

def _ensure_dc_layout(ws) -> Tuple[int, Dict[str, int], int]:
    # Header
    h_r, h_c = _find_cell(ws, "DelayCondition")
    if h_r is None:
        h_r, h_c = 1, 1
        ws.cell(row=h_r, column=h_c, value="DelayCondition")
    # Labels
    labels = ["Condition", "Target", "Delay_Min", "Delay_Max"]
    lab_row = h_r + 1
    col_map: Dict[str, int] = {}
    for i, lab in enumerate(labels):
        c = h_c + i
        if not ws.cell(row=lab_row, column=c).value:
            ws.cell(row=lab_row, column=c, value=lab)
        col_map[lab] = c
    return h_r, col_map, lab_row + 1

def _update_delay_sheet(ws, cfg: Dict[str, Any]) -> int:
    h_r, cols, data_start = _ensure_dc_layout(ws)
    # find first empty row at Condition col
    r = data_start
    while True:
        v = ws.cell(row=r, column=cols["Condition"]).value
        if v is None or str(v).strip() == "":
            break
        r += 1
    ws.cell(row=r, column=cols["Condition"], value=cfg.get("Condition", ""))
    ws.cell(row=r, column=cols["Target"],    value=cfg.get("Target", ""))
    ws.cell(row=r, column=cols["Delay_Min"], value=cfg.get("Delay_Min", "1"))
    ws.cell(row=r, column=cols["Delay_Max"], value=cfg.get("Delay_Max", "1"))
    # Ensure Base Clock/Reset labels exist below header
    clk_r, clk_c = _find_cell(ws, "Base Clock")
    rst_r, rst_c = _find_cell(ws, "Base Reset")
    if clk_r is None:
        clk_r, clk_c = h_r + 3, 1
        ws.cell(row=clk_r, column=clk_c, value="Base Clock")
    if rst_r is None:
        rst_r, rst_c = h_r + 4, 1
        ws.cell(row=rst_r, column=rst_c, value="Base Reset")
    return r

def _sv_header() -> str:
    return '`include "uvm_macros.svh"\nimport uvm_pkg::*;\n\n'

def _nz(s: Optional[str], placeholder: str) -> str:
    return (s or "").strip() or placeholder

# Updated builders to match spec (names: delayCondition, Trigger/Result)
def _build_delay_sv(clk: str, rst: str, trig: str, res: str,
                    w_clk: str, w_rst: str, w_trig: str, w_res: str,
                    dmin: str, dmax: str,
                    exp_min: str, exp_max: str) -> str:
    lines: List[str] = []
    lines.append(_sv_header())
    lines.append("module assertion_delayCondition")
    lines.append("(")
    lines.append(f"    {_fmt_input_decl(clk,  w_clk)},")
    lines.append(f"    {_fmt_input_decl(rst,  w_rst)},")
    lines.append(f"    {_fmt_input_decl(trig, w_trig)},")
    lines.append(f"    {_fmt_input_decl(res,  w_res)},")
    lines.append(");")
    lines.append("")
    # expected values as localparams for validity
    lines.append(f"localparam int expected_min_value = {exp_min};")
    lines.append(f"localparam int expected_max_value = {exp_max};")
    lines.append("")
    lines.append("property p_delayCondition_check1(trigger, result);")
    lines.append(f"    @(posedge {clk}) disable iff(!{rst})")
    lines.append(f"    $rose(trigger) |-> ##[{dmin} : {dmax}] $rose(result);")
    lines.append("endproperty")
    lines.append("")
    lines.append(f'assert property (p_delayCondition_check1({trig}, {res})) else $error("failed at %t", $time);')
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)

def _build_delay_inst_sv(clk: str, rst: str, trig: str, res: str) -> str:
    lines: List[str] = []
    lines.append(_sv_header())
    lines.append("assertion_delayCondition u_assertion_delayCondition();")
    lines.append("")
    lines.append(f"assign u_assertion_delayCondition.{clk}  = top.dut.{clk};")
    lines.append(f"assign u_assertion_delayCondition.{rst}  = top.dut.{rst};")
    lines.append(f"assign u_assertion_delayCondition.{trig} = top.dut.{trig};")
    lines.append(f"assign u_assertion_delayCondition.{res}  = top.dut.{res};")
    lines.append("")
    return "\n".join(lines)

# -----------------------------
# Plugin
# -----------------------------
@register
class DelayConditionPlugin(BaseAssertionPlugin):
    plugin_name = "delayCondition"
    sheet_name = "DelayCondition"

    def parse(self, xls_path: Path) -> Dict[str, Any]:
        # 0) Load module info
        mod = _load_module_define(Path(xls_path))

        # 1) Open sheet and ensure header exists
        wb_w = load_workbook(xls_path)
        try:
            ws_w = _get_sheet_ci(wb_w, self.sheet_name, create=False)
        except KeyError:
            ws_w = _get_sheet_ci(wb_w, self.sheet_name, create=True)
        # Ensure header label
        if _find_cell(ws_w, "DelayCondition")[0] is None:
            ws_w.cell(row=1, column=1, value="DelayCondition")

        # 2) Base Clock/Reset from label-right (resolve references, no prompts)
        clk = _read_label_right_resolved(wb_w, ws_w, "Base Clock")
        rst = _read_label_right_resolved(wb_w, ws_w, "Base Reset")

        # 3) Trigger: DUT inputs or 0=Custom
        trig = _pick_one("Select Trigger signal", _signal_options(mod), allow_custom=True)
        _write_label_below(ws_w, "Trigger", trig)

        # 4) Delay1/Delay2 (numbers)
        def _ask_int(prompt: str, default: str) -> str:
            while True:
                s = input(f"{prompt} (integer, default {default}): ").strip() or default
                if s.isdigit():
                    return s
                print("Invalid integer. Try again.")
        dmin = _ask_int("Enter Delay1", "1")
        dmax = _ask_int("Enter Delay2", dmin)
        _write_label_below(ws_w, "Delay1", dmin)
        _write_label_below(ws_w, "Delay2", dmax)

        # 5) Result: DUT inputs or 0=Custom
        res = _pick_one("Select Result signal", _signal_options(mod), allow_custom=True)
        _write_label_below(ws_w, "Result", res)

        # 6) expected min/max: 프롬프트 없이 기본값 사용
        exp_min = "0"
        exp_max = "0"

        wb_w.save(xls_path)

        # 7) Reopen and read final values (sheet)
        wb = load_workbook(xls_path, data_only=True)
        ws = _get_sheet_ci(wb, self.sheet_name, create=False)
        clk_do, rst_do = _read_base_clk_rst(ws)
        # data_only가 비어 있으면 수식 역참조로 보완
        if not clk_do:
            clk_do = _read_label_right_resolved(wb_w, ws_w, "Base Clock")
        if not rst_do:
            rst_do = _read_label_right_resolved(wb_w, ws_w, "Base Reset")
        clk = clk_do or clk
        rst = rst_do or rst
        trig = _read_label_below(ws, "Trigger") or trig
        dmin = _read_label_below(ws, "Delay1") or dmin
        dmax = _read_label_below(ws, "Delay2") or dmax
        res = _read_label_below(ws, "Result") or res

        # 8) widths
        w_clk  = _port_width_token(mod, clk)
        w_rst  = _port_width_token(mod, rst)
        w_trig = _port_width_token(mod, trig)
        w_res  = _port_width_token(mod, res)

        # 9) blocks (always create)
        blocks: List[Dict[str, Any]] = [{
            "Base Clock": clk or "",
            "Base Reset": rst or "",
            "Trigger": trig or "",
            "Delay1": dmin or "1",
            "Delay2": dmax or (dmin or "1"),
            "Result": res or "",
            "Expected_Min_Value": exp_min or "0",
            "Expected_Max_Value": exp_max or "0",
            "Base Clock Width": w_clk or "[0:0]",
            "Base Reset Width": w_rst or "[0:0]",
            "Trigger Width": w_trig or "[0:0]",
            "Result Width": w_res or "[0:0]",
        }]
        return {"blocks": blocks}

    def generate_sv(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        out_dir = Path(context.get("output_dir") or context.get("session_dir") or ".")
        out_dir.mkdir(parents=True, exist_ok=True)

        snippets: List[str] = []
        for b in (parsed.get("blocks") or []):
            clk = b.get("Base Clock", ""); rst = b.get("Base Reset", "")
            trig = b.get("Trigger", "");   res = b.get("Result", "")
            dmin = b.get("Delay1", "1");   dmax = b.get("Delay2", "1")
            exp_min = b.get("Expected_Min_Value", "0")
            exp_max = b.get("Expected_Max_Value", "0")
            w_clk  = b.get("Base Clock Width", "[0:0]")
            w_rst  = b.get("Base Reset Width", "[0:0]")
            w_trig = b.get("Trigger Width", "[0:0]")
            w_res  = b.get("Result Width", "[0:0]")

            clk_p  = _nz(clk,  "UNDEF_CLK")
            rst_p  = _nz(rst,  "UNDEF_RST")
            trig_p = _nz(trig, "UNDEF_TRIGGER")
            res_p  = _nz(res,  "UNDEF_RESULT")
            dmin_p = (str(dmin).strip() or "1")
            dmax_p = (str(dmax).strip() or dmin_p)
            exp_min_p = str(exp_min).strip() or "0"
            exp_max_p = str(exp_max).strip() or "0"

            sv = _build_delay_sv(clk_p, rst_p, trig_p, res_p, w_clk, w_rst, w_trig, w_res, dmin_p, dmax_p, exp_min_p, exp_max_p)
            inst_sv = _build_delay_inst_sv(clk_p, rst_p, trig_p, res_p)

            (out_dir / "assertion_delayCondition.sv").write_text(sv, encoding="utf-8")
            (out_dir / "assertion_delayCondition_inst.sv").write_text(inst_sv, encoding="utf-8")
            snippets.append(sv)
        return snippets

    def emit_json(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return parsed