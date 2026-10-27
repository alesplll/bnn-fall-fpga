`timescale 1ns / 1ps

// Experimental three-stage version of bnn_classifier.
// Stage 1 registers the input, stage 2 the eight hidden bits, and
// stage 3 the decision. The numerical calculation is unchanged.
module bnn_classifier_pipelined #(
    parameter W_A_FILE = "weights_layerA_W.mem",
    parameter B_A_FILE = "weights_layerA_b.mem",
    parameter W_B_FILE = "weights_layerB_W.mem",
    parameter B_B_FILE = "weights_layerB_b.mem"
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [39:0] input_features,
    output reg         valid_out,
    output reg         fall_detected
);
    reg [7:0]  w_a [0:39];
    reg [31:0] b_a [0:7];
    reg        w_b [0:7];
    reg [31:0] b_b [0:0];

    initial begin
        $readmemh(W_A_FILE, w_a);
        $readmemh(B_A_FILE, b_a);
        $readmemh(W_B_FILE, w_b);
        $readmemh(B_B_FILE, b_b);
    end

    reg [39:0] input_q;
    reg        valid_input_q;
    reg [7:0]  hidden_q;
    reg        valid_hidden_q;

    reg signed [15:0] product;
    reg signed [31:0] accumulator;
    reg [7:0] hidden_next;
    integer h;
    integer j;

    always @* begin
        product = 16'sd0;
        accumulator = 32'sd0;
        hidden_next = 8'b0;
        for (h = 0; h < 8; h = h + 1) begin
            accumulator = $signed(b_a[h]);
            for (j = 0; j < 5; j = j + 1) begin
                product = $signed(input_q[39 - 8*j -: 8])
                        * $signed(w_a[j*8 + h]);
                accumulator = accumulator + {{16{product[15]}}, product};
            end
            hidden_next[h] = (accumulator >= 32'sd0);
        end
    end

    reg [3:0] matching_bits;
    reg signed [31:0] score;
    reg prediction_next;
    integer k;

    always @* begin
        matching_bits = 4'b0;
        for (k = 0; k < 8; k = k + 1)
            matching_bits = matching_bits + (hidden_q[k] ~^ w_b[k]);
        score = ($signed({28'b0, matching_bits}) <<< 1)
              - 32'sd8 + $signed(b_b[0]);
        prediction_next = (score >= 32'sd0);
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            input_q <= 40'b0;
            valid_input_q <= 1'b0;
            hidden_q <= 8'b0;
            valid_hidden_q <= 1'b0;
            valid_out <= 1'b0;
            fall_detected <= 1'b0;
        end else begin
            input_q <= input_features;
            valid_input_q <= valid_in;
            hidden_q <= hidden_next;
            valid_hidden_q <= valid_input_q;
            valid_out <= valid_hidden_q;
            if (valid_hidden_q)
                fall_detected <= prediction_next;
        end
    end
endmodule
