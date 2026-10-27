`timescale 1ns / 1ps

module tb_bnn_classifier_pipelined;
`ifdef FULL_TEST
    localparam VECTOR_COUNT = 2331;
`elsif EDGE_TEST
    localparam VECTOR_COUNT = 14;
`else
    localparam VECTOR_COUNT = 64;
`endif

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;
    reg valid_in = 1'b0;
    reg [39:0] input_features = 40'b0;
    wire valid_out;
    wire fall_detected;
    reg [39:0] vectors [0:VECTOR_COUNT-1];
    reg expected [0:VECTOR_COUNT-1];
`ifdef FULL_TEST
    reg [7:0] expected_hidden [0:VECTOR_COUNT-1];
    reg [31:0] expected_score [0:VECTOR_COUNT-1];
`elsif EDGE_TEST
    reg [7:0] expected_hidden [0:VECTOR_COUNT-1];
    reg [31:0] expected_score [0:VECTOR_COUNT-1];
`endif
    integer i;
    integer errors;

    bnn_classifier_pipelined dut (
        .clk(clk),
        .rst_n(rst_n),
        .valid_in(valid_in),
        .input_features(input_features),
        .valid_out(valid_out),
        .fall_detected(fall_detected)
    );

    initial begin
`ifdef FULL_TEST
        $readmemh("tb_inputs_full.mem", vectors);
        $readmemh("tb_expected_full.mem", expected);
        $readmemh("tb_hidden_full.mem", expected_hidden);
        $readmemh("tb_score_full.mem", expected_score);
`elsif EDGE_TEST
        $readmemh("tb_inputs_edge.mem", vectors);
        $readmemh("tb_expected_edge.mem", expected);
        $readmemh("tb_hidden_edge.mem", expected_hidden);
        $readmemh("tb_score_edge.mem", expected_score);
`else
        $readmemh("tb_inputs_64.mem", vectors);
        $readmemh("tb_expected_64.mem", expected);
`endif
        errors = 0;
        repeat (2) @(negedge clk);
        if (valid_out !== 1'b0 || fall_detected !== 1'b0)
            $fatal(1, "reset did not clear outputs");
        rst_n = 1'b1;

        for (i = 0; i < VECTOR_COUNT + 2; i = i + 1) begin
            @(negedge clk);
            valid_in = (i < VECTOR_COUNT);
            input_features = (i < VECTOR_COUNT) ? vectors[i] : 40'b0;
            @(posedge clk);
            #1;
`ifdef FULL_TEST
            if (i >= 1 && i - 1 < VECTOR_COUNT) begin
                if (dut.hidden_q !== expected_hidden[i-1]) begin
                    $display("FAIL hidden %0d", i-1);
                    errors = errors + 1;
                end
                if (dut.score !== $signed(expected_score[i-1])) begin
                    $display("FAIL score %0d", i-1);
                    errors = errors + 1;
                end
            end
`elsif EDGE_TEST
            if (i >= 1 && i - 1 < VECTOR_COUNT) begin
                if (dut.hidden_q !== expected_hidden[i-1]) begin
                    $display("FAIL hidden %0d", i-1);
                    errors = errors + 1;
                end
                if (dut.score !== $signed(expected_score[i-1])) begin
                    $display("FAIL score %0d", i-1);
                    errors = errors + 1;
                end
            end
`endif
            if (i >= 2) begin
                if (valid_out !== 1'b1 || fall_detected !== expected[i-2]) begin
                    $display("FAIL output %0d: valid=%b got=%b expected=%b",
                             i-2, valid_out, fall_detected, expected[i-2]);
                    errors = errors + 1;
                end
            end else if (valid_out !== 1'b0) begin
                $display("FAIL early valid at cycle %0d", i);
                errors = errors + 1;
            end
        end

        @(negedge clk);
        valid_in = 1'b0;
        @(posedge clk);
        #1;
        if (valid_out !== 1'b0) begin
            $display("FAIL valid_out did not clear");
            errors = errors + 1;
        end
        if (errors != 0)
            $fatal(1, "%0d failures in %0d vectors", errors, VECTOR_COUNT);
        $display("PASS: pipelined classifier, %0d vectors", VECTOR_COUNT);
        $finish;
    end
endmodule
