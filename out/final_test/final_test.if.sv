`include "uvm_macros.svh"
import uvm_pkg::*;

interface assertion_intf();

// Signal Declarations
logic [0:0] UNDEF_RST;
logic [0:0] clk;
logic [0:0] ready;
logic [0:0] rst;
logic [0:0] valid;

// ========== COUNTER ==========
reg [31:0] cnt;
always @(posedge clk or negedge rst) begin
    if(!rst) begin
        cnt <= 0;
    end
    else if(reset_condition) begin
        cnt <= 0;
    end
    else if(plus_condition) begin
        cnt <= cnt+1;
    end
    else begin
        cnt <= cnt;
    end
end
property p_counter_check;
    @(posedge clk) disable iff(!rst)
    trigger_condition |-> (cnt == expect_count_value);
endproperty
assert property (p_counter_check) else `uvm_error("ASSERTION", "Counter check failed")

// ========== HANDSHAKE ==========
property p_ready_valid_check(ready, valid);
    @(posedge clk) disable iff(!rst)
    valid && !ready |-> ##[1:$] (ready || (valid && !ready));
endproperty
assert property (p_ready_valid_check(valid, ready)) else `uvm_error("ASSERTION", "Ready-Valid check failed")

endinterface
