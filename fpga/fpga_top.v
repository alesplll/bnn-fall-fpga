`timescale 1ns / 1ps

// Board-independent FPGA prototype. A small ROM feeds the classifier with
// 64 reference inputs prepared in practice 1; the outputs are checked on chip.
module fpga_top (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    output reg        busy,
    output reg        done,
    output reg        pass,
    output reg [6:0]  checked_count,
    output reg [6:0]  error_count,
    output reg        last_prediction
);
    localparam [1:0] IDLE = 2'd0;
    localparam [1:0] DRIVE = 2'd1;
    localparam [1:0] CHECK = 2'd2;

    reg [1:0] state;
    reg [5:0] vector_index;
    reg [39:0] vectors [0:63];
    reg expected [0:63];

    initial begin
        $readmemh("tb_inputs_64.mem", vectors);
        $readmemh("tb_expected_64.mem", expected);
    end

    wire [39:0] input_features = vectors[vector_index];
    wire valid_in = (state == DRIVE);
    wire valid_out;
    wire fall_detected;
    wire mismatch = (valid_out != 1'b1) ||
                    (fall_detected != expected[vector_index]);

    bnn_classifier classifier (
        .clk(clk),
        .rst_n(rst_n),
        .valid_in(valid_in),
        .input_features(input_features),
        .valid_out(valid_out),
        .fall_detected(fall_detected)
    );

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            vector_index <= 6'd0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            checked_count <= 7'd0;
            error_count <= 7'd0;
            last_prediction <= 1'b0;
        end else begin
            case (state)
                IDLE: begin
                    if (start) begin
                        vector_index <= 6'd0;
                        busy <= 1'b1;
                        done <= 1'b0;
                        pass <= 1'b0;
                        checked_count <= 7'd0;
                        error_count <= 7'd0;
                        state <= DRIVE;
                    end
                end
                DRIVE: state <= CHECK;
                CHECK: begin
                    checked_count <= checked_count + 7'd1;
                    last_prediction <= fall_detected;
                    if (mismatch)
                        error_count <= error_count + 7'd1;
                    if (vector_index == 6'd63) begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        pass <= (error_count == 7'd0) && !mismatch;
                        state <= IDLE;
                    end else begin
                        vector_index <= vector_index + 6'd1;
                        state <= DRIVE;
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
