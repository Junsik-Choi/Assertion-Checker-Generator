`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_2phase
 u_assertion_2phase ();

assign u_assertion_2phase.clk = top.dut.clk;
assign u_assertion_2phase.i_resetn = top.dut.i_resetn;
assign u_assertion_2phase.req = top.dut.req;
assign u_assertion_2phase.ack = top.dut.ack;
