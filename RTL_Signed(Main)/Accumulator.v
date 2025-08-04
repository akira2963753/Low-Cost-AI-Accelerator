module Accumulator #(
    parameter SIZE = 8,
    parameter PARTIAL_SUM_WIDTH = ((8 * 4) + 4) + SIZE + 1, // Size of the partial sum
    parameter COMPENSATION_PARTIAL_SUM_WIDTH = 8 + 5 + 1
)(
    input clk,
    input [2:0] Acc_Wr_Addr,
    input ACC_Wr_en,
    input [2:0] CAcc_Wr_Addr,
    input CACC_Wr_en,
    input Acc_Rd_en,
    input [2:0] Acc_Rd_Addr,
    input signed [COMPENSATION_PARTIAL_SUM_WIDTH-1:0] Compensation_Partial_Sum_in,
    input signed [PARTIAL_SUM_WIDTH-1:0] Partial_Sum_in,
    output reg signed [PARTIAL_SUM_WIDTH-1:0] Partial_Sum_out
);
   
    reg signed [PARTIAL_SUM_WIDTH-1:0] Partial_Sum_Mem [0:7];

    always @(posedge clk) begin // Two port write mem
        if(ACC_Wr_en) Partial_Sum_Mem[Acc_Wr_Addr] <= Partial_Sum_in + Partial_Sum_Mem[Acc_Wr_Addr];
        else;
        if(CACC_Wr_en) Partial_Sum_Mem[CAcc_Wr_Addr] <= Compensation_Partial_Sum_in;
        else;
    end
    
    always @(posedge clk) begin
        if(Acc_Rd_en) Partial_Sum_out <= Partial_Sum_Mem[Acc_Rd_Addr];
        else;
    end

   


endmodule