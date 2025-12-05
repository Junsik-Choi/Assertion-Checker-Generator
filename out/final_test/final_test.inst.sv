`include "uvm_macros.svh"
import uvm_pkg::*;

assertion_intf u_assertion_intf();

assign u_assertion_intf.clk = top.dut.clk;
assign u_assertion_intf.UNDEF_RST = top.dut.UNDEF_RST;
assign u_assertion_intf.rst = top.dut.rst;
assign u_assertion_intf.valid = top.dut.valid;
assign u_assertion_intf.ready = top.dut.ready;
assign u_assertion_intf.req = top.dut.req;
assign u_assertion_intf.ack = top.dut.ack;
