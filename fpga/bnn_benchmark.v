`timescale 1ns / 1ps

// Common registered input for a fair internal clock-path comparison.
// The input features remain variable instead of being fixed in a test ROM.
module bnn_benchmark_shell #(
    parameter PIPELINED = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [39:0] input_features,
    output wire        valid_out,
    output wire        fall_detected
);
    reg [39:0] input_q;
    reg valid_q;

    always @(posedge clk) begin
        if (!rst_n) begin
            input_q <= 40'b0;
            valid_q <= 1'b0;
        end else begin
            input_q <= input_features;
            valid_q <= valid_in;
        end
    end

    generate
        if (PIPELINED) begin : with_register
            bnn_classifier_pipelined classifier (
                .clk(clk), .rst_n(rst_n), .valid_in(valid_q),
                .input_features(input_q),
                .valid_out(valid_out), .fall_detected(fall_detected)
            );
        end else begin : without_register
            bnn_classifier_modular classifier (
                .clk(clk), .rst_n(rst_n), .valid_in(valid_q),
                .input_features(input_q),
                .valid_out(valid_out), .fall_detected(fall_detected)
            );
        end
    endgenerate
endmodule

module bnn_benchmark_baseline (
    input wire clk, rst_n, valid_in,
    input wire [39:0] input_features,
    output wire valid_out, fall_detected
);
    bnn_benchmark_shell #(.PIPELINED(0)) shell (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .input_features(input_features),
        .valid_out(valid_out), .fall_detected(fall_detected)
    );
endmodule

module bnn_benchmark_pipelined (
    input wire clk, rst_n, valid_in,
    input wire [39:0] input_features,
    output wire valid_out, fall_detected
);
    bnn_benchmark_shell #(.PIPELINED(1)) shell (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .input_features(input_features),
        .valid_out(valid_out), .fall_detected(fall_detected)
    );
endmodule
