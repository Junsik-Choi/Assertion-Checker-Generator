`include "uvm_macros.svh"
import uvm_pkg::*;


assertion_delayCondition u_assertion_delayCondition();

assign u_assertion_delayCondition.I_CLK  = top.dut.I_CLK;
assign u_assertion_delayCondition.I_RSTN  = top.dut.I_RSTN;
assign u_assertion_delayCondition.I_DATA  = top.dut.I_DATA;
assign u_assertion_delayCondition.I_DEN  = top.dut.I_DEN;
assign u_assertion_delayCondition.I_HSYNC  = top.dut.I_HSYNC;
assign u_assertion_delayCondition.I_VSYNC  = top.dut.I_VSYNC;
