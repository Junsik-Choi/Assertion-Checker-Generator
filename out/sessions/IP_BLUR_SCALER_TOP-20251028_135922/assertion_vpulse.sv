`include "uvm_macros.svh"
import uvm_pkg::*;


module assertion_vpulse
(
    input logic [0:0] I_CLK,
    input logic [0:0] I_RSTN,
    input logic [0:0] $fell(i_PSEL),
    input logic [0:0] I_DEN,
    input logic [0:0] I_HSYNC,
    input logic [0:0] (|O_DEN)
);

sequence s_vpulse(value_count);
    @(negedge $fell(i_PSEL))
    (I_DEN, value_count = value_count + 1)[*0:$]
    ##1 (!I_DEN);
endsequence

property p_vpulse(count_trigger, target_pulse, expected_min_value, expected_max_value);
    int value_count;
    @(posedge I_CLK) disable iff(!I_RSTN)
    $rose(target_pulse) |-> (1, value_count = 0)
    ##0 s_vpulse(value_count)
    ##1 (expected_min_value <= value_count && value_count <= expected_max_value);
endproperty

assert property (p_vpulse($fell(i_PSEL), I_DEN, I_HSYNC, (|O_DEN)))
    else $error("failed at %t", $time);

endmodule
