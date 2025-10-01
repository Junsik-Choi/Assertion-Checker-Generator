from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

import sys
from openpyxl import load_workbook

def find_cell(ws, value):
    """시트에서 value와 일치하는 셀을 찾아 위치(row, col) 반환"""
    for row in ws.iter_rows():
        for cell in row:
            if str(cell.value).strip() == value:
                return cell.row, cell.column
    return None, None

def parse_handshake_block_for_row(ws, row, type_col):
    # 'Base Clock'과 'Base Reset' 셀 위치 및 값 찾기 (한 칸 오른쪽 값 파싱)
    base_clk_row, base_clk_col = find_cell(ws, "Base Clock")
    base_reset_row, base_reset_col = find_cell(ws, "Base Reset")
    if base_clk_row is None or base_reset_row is None:
        raise ValueError("'Base Clock' 또는 'Base Reset' 셀을 찾을 수 없습니다.")

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
    # assertion_<Type>_inst.sv 파일 내용 생성
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

def main(xlsx_path):
    wb = load_workbook(xlsx_path, data_only=True)
    # 'handshake' 시트 선택
    if 'handshake' not in wb.sheetnames:
        print(f"엑셀 파일에 'handshake' 시트가 없습니다. 시트 목록: {wb.sheetnames}")
        sys.exit(1)
    ws = wb['handshake']

    # 결과 파일 저장 폴더 생성
    output_dir = Path("handshake_output")
    output_dir.mkdir(exist_ok=True)

    # Type 셀 위치 찾기
    handshake_row, handshake_col = find_cell(ws, "Handshake")
    for merged_range in ws.merged_cells.ranges:
        if ws.cell(row=handshake_row, column=handshake_col).coordinate in merged_range:
            min_col = merged_range.min_col
            break
    else:
        min_col = handshake_col
    type_row = handshake_row + 1
    type_col = min_col

    # Type 아래 셀들에서 값 추출 (공란 나올 때까지 반복)
    r = type_row + 1
    while r <= ws.max_row:
        val = ws.cell(row=r, column=type_col).value
        if val is None or not str(val).strip():
            break
        phase_val_str = str(val).strip().lower()
        if phase_val_str in ("4phase", "2phase"):
            # 각 phase별로 assertion 파일 생성
            info = parse_handshake_block_for_row(ws, r, type_col)
            verilog_code = generate_verilog(info)
            output_path = output_dir / f"assertion_{phase_val_str}.sv"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(verilog_code)
            print(f"Verilog 코드가 '{output_path}' 파일에 저장되었습니다.")

            # inst 파일 생성
            inst_verilog_code = generate_inst_verilog(info)
            inst_output_path = output_dir / f"assertion_{phase_val_str}_inst.sv"
            with open(inst_output_path, "w", encoding="utf-8") as f:
                f.write(inst_verilog_code)
            print(f"Inst 코드가 '{inst_output_path}' 파일에 저장되었습니다.")
        r += 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python handshake.py <excel_file.xlsx>")
        sys.exit(1)
    main(sys.argv[1])


