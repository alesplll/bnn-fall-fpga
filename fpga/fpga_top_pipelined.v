`timescale 1ns / 1ps

// Separate experiment; the completed PR3 fpga_top remains unchanged.
module fpga_top_pipelined (
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
    localparam [1:0] SEND = 2'd1;
    localparam [1:0] DRAIN = 2'd2;

    reg [1:0] state;
    reg [5:0] send_index;
    reg [5:0] check_index_q0;
    reg [5:0] check_index_q1;
    reg [5:0] check_index_q2;
    reg [39:0] vectors [0:63];
    reg expected [0:63];

    initial begin
        $readmemh("tb_inputs_64.mem", vectors);
        $readmemh("tb_expected_64.mem", expected);
    end

    wire [39:0] input_features = vectors[send_index];
    wire valid_in = (state == SEND);
    wire valid_out;
    wire fall_detected;
    wire mismatch = (fall_detected != expected[check_index_q2]);

    bnn_classifier_pipelined classifier (
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
            send_index <= 6'd0;
            check_index_q0 <= 6'd0;
            check_index_q1 <= 6'd0;
            check_index_q2 <= 6'd0;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            checked_count <= 7'd0;
            error_count <= 7'd0;
            last_prediction <= 1'b0;
        end else begin
            check_index_q0 <= send_index;
            check_index_q1 <= check_index_q0;
            check_index_q2 <= check_index_q1;
            case (state)
                IDLE: begin
                    if (start) begin
                        send_index <= 6'd0;
                        busy <= 1'b1;
                        done <= 1'b0;
                        pass <= 1'b0;
                        checked_count <= 7'd0;
                        error_count <= 7'd0;
                        state <= SEND;
                    end
                end
                SEND: begin
                    if (send_index == 6'd63)
                        state <= DRAIN;
                    else
                        send_index <= send_index + 6'd1;
                end
                DRAIN: begin end
                default: state <= IDLE;
            endcase
            if (valid_out && state != IDLE) begin
                checked_count <= checked_count + 7'd1;
                last_prediction <= fall_detected;
                if (mismatch)
                    error_count <= error_count + 7'd1;
                if (checked_count == 7'd63) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    pass <= (error_count == 7'd0) && !mismatch;
                    state <= IDLE;
                end
            end
        end
    end
endmodule
