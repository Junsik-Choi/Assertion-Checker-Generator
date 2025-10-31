`include "uvm_macros.svh"
import uvm_pkg::*;


assertion_vpulse
 u_assertion_vpulse ();

assign u_assertion_vpulse.I_CLK = top.dut.I_CLK;
assign u_assertion_vpulse.I_RSTN = top.dut.I_RSTN;
assign u_assertion_vpulse.$fell(i_PSEL) = top.dut.$fell(i_PSEL);
assign u_assertion_vpulse.I_DEN = top.dut.I_DEN;
assign u_assertion_vpulse.I_HSYNC = top.dut.I_HSYNC;
assign u_assertion_vpulse.(|O_DEN) = top.dut.(|O_DEN);
