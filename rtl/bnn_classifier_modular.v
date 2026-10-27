`timescale 1ns / 1ps

// Same two layer modules as the pipelined core, without an interlayer register.
module bnn_classifier_modular #(
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
    wire [7:0] hidden_bits;
    wire signed [31:0] score;
    wire prediction_next;

    bnn_layer_a #(.W_FILE(W_A_FILE), .B_FILE(B_A_FILE)) layer_a (
        .input_features(input_features),
        .hidden_bits(hidden_bits)
    );

    bnn_layer_b #(.W_FILE(W_B_FILE), .B_FILE(B_B_FILE)) layer_b (
        .hidden_bits(hidden_bits),
        .score(score),
        .prediction(prediction_next)
    );

    always @(posedge clk) begin
        if (!rst_n) begin
            valid_out <= 1'b0;
            fall_detected <= 1'b0;
        end else begin
            valid_out <= valid_in;
            if (valid_in)
                fall_detected <= prediction_next;
        end
    end
endmodule
