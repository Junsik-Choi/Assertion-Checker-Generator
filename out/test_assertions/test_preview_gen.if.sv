`include "uvm_macros.svh"
import uvm_pkg::*;

interface assertion_intf();

// Signal Declarations
logic [0:0] UNDEF_RST;
logic [0:0] i_clk;
logic [0:0] i_rst_n;
logic [0:0] ready;
logic [0:0] valid;

// ========== COUNTER ==========
reg [31:0] cnt;
always @(posedge i_clk or negedge i_rst_n) begin
    if(!i_rst_n) begin
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
    @(posedge i_clk) disable iff(!i_rst_n)
    trigger_condition |-> (cnt == expect_count_value);
endproperty
assert property (p_counter_check) else `uvm_error("ASSERTION", "Counter check failed")

// ========== HANDSHAKE ==========
property p_ready_valid_check(ready, valid);
    @(posedge i_clk) disable iff(!i_rst_n)
    valid && !ready |-> ##[1:$] (ready || (valid && !ready));
endproperty
assert property (p_ready_valid_check(valid, ready)) else `uvm_error("ASSERTION", "Ready-Valid check failed")

endinterface
