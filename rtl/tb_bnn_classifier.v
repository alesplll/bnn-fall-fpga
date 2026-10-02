`timescale 1ns / 1ps

module tb_bnn_classifier;
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

    bnn_classifier dut (
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
            $fatal(1, "synchronous reset did not clear outputs");
        rst_n = 1'b1;

        for (i = 0; i < VECTOR_COUNT; i = i + 1) begin
            @(negedge clk);
            input_features = vectors[i];
            valid_in = 1'b1;
            #1;
`ifdef FULL_TEST
            // Check both layer boundaries before the registered output.
            if (dut.hidden_bits !== expected_hidden[i]) begin
                $display("FAIL vector %0d: hidden=%02h expected=%02h",
                         i, dut.hidden_bits, expected_hidden[i]);
                errors = errors + 1;
            end
            if (dut.score !== $signed(expected_score[i])) begin
                $display("FAIL vector %0d: score=%0d expected=%0d",
                         i, dut.score, $signed(expected_score[i]));
                errors = errors + 1;
            end
`elsif EDGE_TEST
            if (dut.hidden_bits !== expected_hidden[i]) begin
                $display("FAIL edge %0d: hidden=%02h expected=%02h",
                         i, dut.hidden_bits, expected_hidden[i]);
                errors = errors + 1;
            end
            if (dut.score !== $signed(expected_score[i])) begin
                $display("FAIL edge %0d: score=%0d expected=%0d",
                         i, dut.score, $signed(expected_score[i]));
                errors = errors + 1;
            end
`endif
            @(posedge clk);
            #1;
            if (valid_out !== 1'b1 || fall_detected !== expected[i]) begin
                $display("FAIL vector %0d: valid=%b output=%b expected=%b",
                         i, valid_out, fall_detected, expected[i]);
                errors = errors + 1;
            end
        end

        @(negedge clk);
        valid_in = 1'b0;
        @(posedge clk);
        #1;
        if (valid_out !== 1'b0) begin
            $display("FAIL: valid_out did not clear after valid_in");
            errors = errors + 1;
        end

        if (errors != 0)
            $fatal(1, "%0d failures in %0d vectors", errors, VECTOR_COUNT);
        $display("PASS: %0d vectors; output, valid signal and golden model agree", VECTOR_COUNT);
        $finish;
    end
endmodule
