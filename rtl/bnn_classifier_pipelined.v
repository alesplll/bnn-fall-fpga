`timescale 1ns / 1ps

// One register boundary between layers A and B; accepts a vector every clock.
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
    wire [7:0] hidden_next;
    reg [7:0] hidden_q;
    reg valid_hidden_q;
    wire signed [31:0] score;
    wire prediction_next;

    bnn_layer_a #(.W_FILE(W_A_FILE), .B_FILE(B_A_FILE)) layer_a (
        .input_features(input_features),
        .hidden_bits(hidden_next)
    );

    bnn_layer_b #(.W_FILE(W_B_FILE), .B_FILE(B_B_FILE)) layer_b (
        .hidden_bits(hidden_q),
        .score(score),
        .prediction(prediction_next)
    );

    always @(posedge clk) begin
        if (!rst_n) begin
            hidden_q <= 8'b0;
            valid_hidden_q <= 1'b0;
            valid_out <= 1'b0;
            fall_detected <= 1'b0;
        end else begin
            hidden_q <= hidden_next;
            valid_hidden_q <= valid_in;
            valid_out <= valid_hidden_q;
            if (valid_hidden_q)
                fall_detected <= prediction_next;
        end
    end
endmodule
