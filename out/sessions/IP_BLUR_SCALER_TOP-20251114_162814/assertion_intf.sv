import uvm_pkg::*;
`include "uvm_macros.svh"

interface assertion_intf();
    logic [0:0] I_CLK;
    logic [0:0] I_RSTN;
    logic [0:0] I_DEN;
    logic [0:0] I_VSYNC;
    logic [0:0] PCLK;

// counter
reg [31:0] cnt;

always @(posedge I_CLK or negedge I_RSTN) begin
    if(!I_RSTN) begin
        cnt <= 0;
    end
    else if(I_DEN) begin
        cnt <= 0;
    end
    else if(rose(I_DEN) $$ i_enable) begin
        cnt <= cnt+1;
    end
    else begin
        cnt <= cnt;
    end
end

property p_counter_check;
    @(posedge I_CLK) disable iff(!I_RSTN)
    I_VSYNC |-> (cnt == PCLK);
endproperty

assert property (p_counter_check)  else $error("failed at %t", $time);

endinterface
