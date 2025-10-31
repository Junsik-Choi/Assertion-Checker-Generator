`include "uvm_macros.svh"
import uvm_pkg::*;

module assertion_2phase
 (
     input logic clk,
     input logic i_resetn,
     input logic req,
     input logic ack
 );

property p_2phase_check_0(req, ack);
  @(posedge clk) disable iff (!i_resetn)
  (~req & ~ack) |-> ##1 ((req & ~ack) or (req & ack) or (~req & ~ack));
endproperty

property p_2phase_check_1(req, ack);
  @(posedge clk) disable iff (!i_resetn)
  (~req & ack) |-> ##1 ((~req & ~ack) or (~req & ack));
endproperty

property p_2phase_check_2(req, ack);
  @(posedge clk) disable iff (!i_resetn)
  (req & ~ack) |-> ##1 ((req & ack) or (req & ~ack));
endproperty

property p_2phase_check_3(req, ack);
  @(posedge clk) disable iff (!i_resetn)
  (req & ack) |-> ##1 ((~req & ack) or (~req & ~ack) or (req & ack));
endproperty

assert_2ph_0 : assert property (p_2phase_check_0(req, ack)) else $error("failed at %t", $time);
assert_2ph_1 : assert property (p_2phase_check_1(req, ack)) else $error("failed at %t", $time);
assert_2ph_2 : assert property (p_2phase_check_2(req, ack)) else $error("failed at %t", $time);
assert_2ph_3 : assert property (p_2phase_check_3(req, ack)) else $error("failed at %t", $time);

endmodule
