from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

import sys
from openpyxl import load_workbook

from .base import BaseAssertionPlugin
from .registry import register

def find_cell(ws, value):
    """Find the cell in the sheet that matches 'value' and return its position (row, col)"""
    for row in ws.iter_rows():
        for cell in row:
            if str(cell.value).strip() == value:
                return cell.row, cell.column
    return None, None

def parse_handshake_block_for_row(ws, row, type_col):
    # Find the positions and values of 'Base Clock' and 'Base Reset' cells (parse the value one cell to the right)
    base_clk_row, base_clk_col = find_cell(ws, "Base Clock")
    base_reset_row, base_reset_col = find_cell(ws, "Base Reset")
    if base_clk_row is None or base_reset_row is None:
        raise ValueError("Could not find 'Base Clock' or 'Base Reset' cell.")

    base_clk = ws.cell(row=base_clk_row, column=base_clk_col + 1).value
    base_reset = ws.cell(row=base_reset_row, column=base_reset_col + 1).value

    phase_val = ws.cell(row=row, column=type_col).value
    phase_type = str(phase_val).strip().lower()
    sender = ws.cell(row=row, column=type_col + 1).value
    receiver = ws.cell(row=row, column=type_col + 2).value

    return {
        "phase_type": phase_type,
        "Base Clock": base_clk,
        "Reset": base_reset,
        "Sender": sender,
        "Receiver": receiver
    }

def generate_verilog(info):
    # info: dict with phase_type, Base Clock, Reset, Sender, Receiver
    if info["phase_type"] == "4phase":
        template = f'''`include "uvm_macros.svh"
import uvm_pkg::*;

module assertion_4phase
(
    input {info["Base Clock"]},
    input {info["Reset"]},
    input {info["Sender"]},
    input {info["Receiver"]}
);

property p_4ph_check_0(req,ack);
    @(posedge {info["Base Clock"]}) disable iff(!{info["Reset"]})
    (~req & ~ack) |-> ##1 ((req & ~ack) or (req & ack) or (~req & ~ack));
endproperty

property p_4ph_check_1(req,ack);
    @(posedge {info["Base Clock"]}) disable iff(!{info["Reset"]})
    (req & ~ack) |-> ##1 ((req & ack) or (req & ~ack));
endproperty

property p_4ph_check_2(req,ack);
    @(posedge {info["Base Clock"]}) disable iff(!{info["Reset"]})
    (req & ~ack) |-> ##1 ((req & ~ack) or (~req & ~ack) or (req & ack));
endproperty

assert_4ph_0 : assert property (p_4ph_check_0({info["Sender"]}, {info["Receiver"]})) else $error("failed at %t", $time);
assert_4ph_1 : assert property (p_4ph_check_1({info["Sender"]}, {info["Receiver"]})) else $error("failed at %t", $time);
assert_4ph_2 : assert property (p_4ph_check_2({info["Sender"]}, {info["Receiver"]})) else $error("failed at %t", $time);

endmodule
'''
    elif info["phase_type"] == "2phase":
        template = f'''`include "uvm_macros.svh"
import uvm_pkg::*;

module assertion_2phase
(
    input {info["Base Clock"]},
    input {info["Reset"]},
    input {info["Sender"]},
    input {info["Receiver"]}
);

property p_2phase_check_0(req, ack);
    @(posedge {info["Base Clock"]}) disable iff (!{info["Reset"]})
    (~req & ~ack) |-> ##1 ((~req & ~ack) or (req & ack) or (~req & ~ack));
endproperty

property p_2phase_check_1(req, ack);
    @(posedge {info["Base Clock"]}) disable iff (!{info["Reset"]})
    (~req & ack) |-> ##1 ((~req & ~ack) or (~req & ack));
endproperty

property p_2phase_check_2(req, ack);
    @(posedge {info["Base Clock"]}) disable iff (!{info["Reset"]})
    (req & ~ack) |-> ##1 ((req & ack) or (req & ~ack));
endproperty

property p_2phase_check_3(req, ack);
    @(posedge {info["Base Clock"]}) disable iff (!{info["Reset"]})
    (req & ack) |-> ##1 ((~req & ack) or (~req & ~ack) or (req & ack));
endproperty

assert_2ph_0 : assert property (p_2phase_check_0({info["Sender"]}, {info["Receiver"]})) else $error("failed at %t", $time);
assert_2ph_1 : assert property (p_2phase_check_1({info["Sender"]}, {info["Receiver"]})) else $error("failed at %t", $time);
assert_2ph_2 : assert property (p_2phase_check_2({info["Sender"]}, {info["Receiver"]})) else $error("failed at %t", $time);
assert_2ph_3 : assert property (p_2phase_check_3({info["Sender"]}, {info["Receiver"]})) else $error("failed at %t", $time);

endmodule
'''
    else:
        template = "// Unknown phase type"
    return template

def generate_inst_verilog(info):
    # Generates the contents for assertion_<Type>_inst.sv file
    type_name = info["phase_type"]
    base_clk = info["Base Clock"]
    base_reset = info["Reset"]
    sender = info["Sender"]
    receiver = info["Receiver"]
    return f'''assertion_{type_name}
u_assertion_{type_name}();

assign u_assertion_{type_name}.{base_clk} = top.dut.{base_clk};
assign u_assertion_{type_name}.{base_reset} = top.dut.{base_reset};
assign u_assertion_{type_name}.{sender} = top.dut.{sender};
assign u_assertion_{type_name}.{receiver} = top.dut.{receiver};
'''

@register
class HandshakePlugin(BaseAssertionPlugin):
    plugin_name = "handshake"
    sheet_name = "handshake"

    def parse(self, xls_path: Path) -> Dict[str, Any]:
        wb = load_workbook(xls_path, data_only=True)
        if self.sheet_name not in wb.sheetnames:
            raise ValueError(f"'{self.sheet_name}' sheet not found in the Excel file. Sheet list: {wb.sheetnames}")
        ws = wb[self.sheet_name]

        handshake_row, handshake_col = find_cell(ws, "Handshake")
        for merged_range in ws.merged_cells.ranges:
            if ws.cell(row=handshake_row, column=handshake_col).coordinate in merged_range:
                min_col = merged_range.min_col
                break
        else:
            min_col = handshake_col
        type_row = handshake_row + 1
        type_col = min_col

        results = []
        r = type_row + 1
        while r <= ws.max_row:
            val = ws.cell(row=r, column=type_col).value
            if val is None or not str(val).strip():
                break
            phase_val_str = str(val).strip().lower()
            if phase_val_str in ("4phase", "2phase"):
                info = parse_handshake_block_for_row(ws, r, type_col)
                results.append(info)
            r += 1
        return {"blocks": results}

    def generate_sv(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        output = []
        for info in parsed.get("blocks", []):
            output.append(generate_verilog(info))
        return output

    def emit_json(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Optional: emit parsed info as JSON
        return parsed

# Optional: standalone script entry point for legacy usage
def main(xlsx_path):
    plugin = HandshakePlugin()
    parsed = plugin.parse(Path(xlsx_path))
    output_dir = Path("handshake_output")
    output_dir.mkdir(exist_ok=True)
    for info in parsed.get("blocks", []):
        verilog_code = generate_verilog(info)
        output_path = output_dir / f"assertion_{info['phase_type']}.sv"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(verilog_code)
        print(f"Verilog code saved to '{output_path}'.")
        inst_verilog_code = generate_inst_verilog(info)
        inst_output_path = output_dir / f"assertion_{info['phase_type']}_inst.sv"
        with open(inst_output_path, "w", encoding="utf-8") as f:
            f.write(inst_verilog_code)
        print(f"Inst code saved to '{inst_output_path}'.")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])


