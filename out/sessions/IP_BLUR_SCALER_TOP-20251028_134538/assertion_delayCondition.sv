`include "uvm_macros.svh"
import uvm_pkg::*;


module assertion_delayCondition
(
    input logic [0:0] I_CLK,
    input logic [0:0] I_RSTN,
    input logic [7:0] I_DATA,
    input logic [0:0] I_DEN,
    input logic [0:0] I_HSYNC,
    input logic [0:0] I_VSYNC,
);

property p_delayCondition_check1(trigger, result);
    @(posedge I_CLK) disable iff(!I_RSTN)
    $rose(trigger) |-> ##[1 : 2] $rose(result);
endproperty

assert property (p_delayCondition_check1(I_DATA, I_DEN)) else $error("failed at %t", $time);

property p_delayCondition_check2(trigger, result);
    @(posedge I_CLK) disable iff(!I_RSTN)
    $rose(trigger) |-> ##[2 : 2] $rose(result);
endproperty

assert property (p_delayCondition_check2(I_HSYNC, I_VSYNC)) else $error("failed at %t", $time);

endmodule
