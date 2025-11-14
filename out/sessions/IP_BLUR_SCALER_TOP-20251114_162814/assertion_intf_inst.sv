import uvm_pkg::*;
`include "uvm_macros.svh"

assertion_intf
      u_assertion_intf();

assign u_assertion_intf.I_CLK = top.dut.I_CLK;
assign u_assertion_intf.I_RSTN = top.dut.I_RSTN;
assign u_assertion_intf.I_DEN = top.dut.I_DEN;
assign u_assertion_intf.I_VSYNC = top.dut.I_VSYNC;
assign u_assertion_intf.PCLK = top.dut.PCLK;
