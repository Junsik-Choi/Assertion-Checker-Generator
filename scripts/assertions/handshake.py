from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

from openpyxl import load_workbook
from .base import BaseAssertionPlugin
from .registry import register

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

def find_cell(ws, value: str) -> Tuple[Optional[int], Optional[int]]:
    tgt = value.strip().lower()
    for row in ws.iter_rows():
        for c in row:
            if c.value is None:
                continue
            if str(c.value).strip().lower() == tgt:
                return c.row, c.column
    return None, None

def _get_sheet_ci(wb, want_name: str = "Handshake", create: bool = False):
    target = (want_name or "").strip().lower()
    for nm in wb.sheetnames:
        if str(nm).strip().lower() == target:
            return wb[nm]
    if create:
        return wb.create_sheet(title=want_name)
    raise KeyError(f"Worksheet {want_name} does not exist.")

def _ensure_handshake_layout(ws) -> Tuple[int, int, int]:
    h_row, h_col = find_cell(ws, "Handshake")
    if h_row is None:
        h_row, h_col = 1, 1
        ws.cell(row=h_row, column=h_col, value="Handshake")
        ws.cell(row=h_row + 1, column=h_col, value="Type")
        ws.cell(row=h_row + 1, column=h_col + 1, value="Sender")
        ws.cell(row=h_row + 1, column=h_col + 2, value="Receiver")
        ws.cell(row=h_row + 3, column=h_col, value="Base Clock")
        ws.cell(row=h_row + 4, column=h_col, value="Base Reset")
    min_col = h_col
    for mr in ws.merged_cells.ranges:
        if ws.cell(row=h_row, column=h_col).coordinate in mr:
            min_col = mr.min_col
            break
    type_row = h_row + 1
    type_col = min_col
    if not ws.cell(row=type_row, column=type_col).value:
        ws.cell(row=type_row, column=type_col, value="Type")
    if not ws.cell(row=type_row, column=type_col + 1).value:
        ws.cell(row=type_row, column=type_col + 1, value="Sender")
    if not ws.cell(row=type_row, column=type_col + 2).value:
        ws.cell(row=type_row, column=type_col + 2, value="Receiver")
    data_row = type_row + 1
    return h_row, type_col, data_row

def parse_handshake_block_for_row(ws, row: int, type_col: int) -> Dict[str, Any]:
    clk_row, clk_col = find_cell(ws, "Base Clock")
    rst_row, rst_col = find_cell(ws, "Base Reset")
    base_clk = ws.cell(row=clk_row, column=clk_col + 1).value if clk_row else None
    base_rst = ws.cell(row=rst_row, column=rst_col + 1).value if rst_row else None
    phase_val = ws.cell(row=row, column=type_col).value
    phase_type = str(phase_val).strip().lower() if phase_val is not None else ""
    sender = ws.cell(row=row, column=type_col + 1).value
    receiver = ws.cell(row=row, column=type_col + 2).value
    return {
        "phase_type": phase_type or "2phase",
        "Base Clock": str(base_clk).strip() if base_clk else "",
        "Reset": str(base_rst).strip() if base_rst else "",
        "Sender": str(sender).strip() if sender else "",
        "Receiver": str(receiver).strip() if receiver else "",
    }

def _auto_pick_clk_rst(mod: Dict[str, Any]) -> Tuple[str, str]:
    clk = ""
    rst = ""
    clocks = mod.get("clocks") or []
    resets = mod.get("resets") or []
    if clocks:
        clk = clocks[0].get("name") or ""
    if resets:
        rst = resets[0].get("name") or ""
    if not clk:
        for it in mod.get("inputs", []):
            n = (it.get("name") or "").lower()
            if "clk" in n or n.endswith("clock"):
                clk = it.get("name") or ""
                break
    if not rst:
        for it in mod.get("inputs", []):
            n = (it.get("name") or "").lower()
            if "rst" in n or "reset" in n:
                rst = it.get("name") or ""
                break
    return clk, rst

def _update_handshake_sheet(ws, hs_cfg: Dict[str, str], module_info: Dict[str, Any]) -> None:
    h_row, type_col, data_row = _ensure_handshake_layout(ws)
    ws.cell(row=data_row, column=type_col, value=hs_cfg.get("phase_type", "2phase"))
    ws.cell(row=data_row, column=type_col + 1, value=hs_cfg.get("sender", ""))
    ws.cell(row=data_row, column=type_col + 2, value=hs_cfg.get("receiver", ""))
    clk_label = find_cell(ws, "Base Clock")
    rst_label = find_cell(ws, "Base Reset")
    if clk_label[0] is None:
        ws.cell(row=h_row + 3, column=type_col, value="Base Clock")
        clk_label = (h_row + 3, type_col)
    if rst_label[0] is None:
        ws.cell(row=h_row + 4, column=type_col, value="Base Reset")
        rst_label = (h_row + 4, type_col)
    clk_name, rst_name = _auto_pick_clk_rst(module_info)
    if clk_name:
        ws.cell(row=clk_label[0], column=clk_label[1] + 1, value=clk_name)
    if rst_name:
        ws.cell(row=rst_label[0], column=rst_label[1] + 1, value=rst_name)

def generate_verilog(info: Dict[str, Any]) -> str:
    clk = info["Base Clock"]; rst = info["Reset"]
    s = info["Sender"]; r = info["Receiver"]
    header = '`include "uvm_macros.svh"\nimport uvm_pkg::*;\n\n'
    if info["phase_type"] == "4phase":
        return header + f"""module assertion_4phase
 (
     input logic {clk},
     input logic {rst},
     input logic {s},
     input logic {r}
 );

property p_4ph_check_0(req,ack);
    @(posedge {clk}) disable iff(!{rst})
    (~req & ~ack) |-> ##1 ((req & ~ack) or (req & ack) or (~req & ~ack));
endproperty

property p_4ph_check_1(req,ack);
    @(posedge {clk}) disable iff(!{rst})
    (req & ~ack) |-> ##1 ((req & ack) or (req & ~ack));
endproperty

property p_4ph_check_2(req,ack);
    @(posedge {clk}) disable iff(!{rst})
    (req & ~ack) |-> ##1 ((req & ~ack) or (~req & ~ack) or (req & ack));
endproperty

assert_4ph_0 : assert property (p_4ph_check_0({s}, {r})) else $error("failed at %t", $time);
assert_4ph_1 : assert property (p_4ph_check_1({s}, {r})) else $error("failed at %t", $time);
assert_4ph_2 : assert property (p_4ph_check_2({s}, {r})) else $error("failed at %t", $time);

endmodule
"""
    else:
        return header + f"""module assertion_2phase
 (
     input logic {clk},
     input logic {rst},
     input logic {s},
     input logic {r}
 );

property p_2phase_check_0(req, ack);
  @(posedge {clk}) disable iff (!{rst})
  (~req & ~ack) |-> ##1 ((req & ~ack) or (req & ack) or (~req & ~ack));
endproperty

property p_2phase_check_1(req, ack);
  @(posedge {clk}) disable iff (!{rst})
  (~req & ack) |-> ##1 ((~req & ~ack) or (~req & ack));
endproperty

property p_2phase_check_2(req, ack);
  @(posedge {clk}) disable iff (!{rst})
  (req & ~ack) |-> ##1 ((req & ack) or (req & ~ack));
endproperty

property p_2phase_check_3(req, ack);
  @(posedge {clk}) disable iff (!{rst})
  (req & ack) |-> ##1 ((~req & ack) or (~req & ~ack) or (req & ack));
endproperty

assert_2ph_0 : assert property (p_2phase_check_0({s}, {r})) else $error("failed at %t", $time);
assert_2ph_1 : assert property (p_2phase_check_1({s}, {r})) else $error("failed at %t", $time);
assert_2ph_2 : assert property (p_2phase_check_2({s}, {r})) else $error("failed at %t", $time);
assert_2ph_3 : assert property (p_2phase_check_3({s}, {r})) else $error("failed at %t", $time);

endmodule
"""

def generate_inst_verilog(info: Dict[str, Any]) -> str:
    clk = info["Base Clock"]; rst = info["Reset"]
    s = info["Sender"]; r = info["Receiver"]
    phase = info["phase_type"] or "2phase"
    mod = f"assertion_{phase}"
    header = '`include "uvm_macros.svh"\nimport uvm_pkg::*;\n\n'
    return header + f"""module assertion_{phase}_inst
 (
     input logic {clk},
     input logic {rst},
     input logic {s},
     input logic {r}
 );

{mod} u_{mod} (
    .{clk}({clk}),
    .{rst}({rst}),
    .{s}({s}),
    .{r}({r})
 );

endmodule
"""

@register
class HandshakePlugin(BaseAssertionPlugin):
    plugin_name = "handshake"
    sheet_name = "Handshake"

    def _load_module_define(self, xls_path: Path) -> Dict[str, Any]:
        try:
            md = xls_path.parent / "module_define.json"
            if md.exists():
                return json.loads(md.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _interactive_collect(self, mod: Dict[str, Any]) -> Dict[str, str]:
        phase = _pick_one("Select handshake phase", [("2phase", "2phase"), ("4phase", "4phase")])
        in_names = [(f"in : {p.get('name')}", p.get("name") or "") for p in (mod.get("inputs") or []) if p.get("name")]
        out_names = [(f"out: {p.get('name')}", p.get("name") or "") for p in (mod.get("outputs") or []) if p.get("name")]
        sig_opts = in_names + out_names or [("manual input", "")]
        sender = _pick_one("Select Sender signal", sig_opts, allow_custom=True)
        receiver = _pick_one("Select Receiver signal", sig_opts, allow_custom=True)
        return {"phase_type": phase or "2phase", "sender": sender, "receiver": receiver}

    def parse(self, xls_path: Path) -> Dict[str, Any]:
        # 1) 플러그인 선택 직후: 타입/신호 선택 프롬프트
        mod = self._load_module_define(Path(xls_path))
        hs_cfg = self._interactive_collect(mod)

        # 2) Excel에 기록(Handshake 시트 이름 대소문자 무시)
        wb_w = load_workbook(xls_path)
        try:
            ws_w = _get_sheet_ci(wb_w, self.sheet_name, create=False)
        except KeyError:
            ws_w = _get_sheet_ci(wb_w, self.sheet_name, create=True)
        _update_handshake_sheet(ws_w, hs_cfg, mod)
        wb_w.save(xls_path)

        # 3) data_only로 재오픈하여 파싱
        wb = load_workbook(xls_path, data_only=True)
        try:
            ws = _get_sheet_ci(wb, self.sheet_name, create=False)
        except KeyError:
            return {"blocks": []}
        h_row, type_col, data_row = _ensure_handshake_layout(ws)
        info = parse_handshake_block_for_row(ws, data_row, type_col)
        blocks: List[Dict[str, Any]] = []
        if info.get("Sender") and info.get("Receiver"):
            blocks.append(info)
        return {"blocks": blocks}

    def generate_sv(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        out_dir = Path(context.get("output_dir") or context.get("session_dir") or ".")
        out_dir.mkdir(parents=True, exist_ok=True)
        snippets: List[str] = []
        for info in parsed.get("blocks", []):
            phase = info.get("phase_type", "2phase")
            sv = generate_verilog(info)
            inst_sv = generate_inst_verilog(info)
            (out_dir / f"assertion_{phase}.sv").write_text(sv, encoding="utf-8")
            (out_dir / f"assertion_{phase}_inst.sv").write_text(inst_sv, encoding="utf-8")
            snippets.append(sv)
        return snippets

    def emit_json(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return parsed

# Optional: standalone script entry point for legacy usage
def main(xlsx_path: str) -> None:
    # 간단 실행 테스트: 시트 준비만 수행
    wb = load_workbook(xlsx_path)
    try:
        ws = _get_sheet_ci(wb, "Handshake", create=False)
    except KeyError:
        ws = _get_sheet_ci(wb, "Handshake", create=True)
    _ensure_handshake_layout(ws)
    wb.save(xlsx_path)


