`timescale 1ns / 1ps

// Port-only testbench also works with a synthesized functional netlist.
`ifdef PIPELINED
module tb_bnn_benchmark_pipeline;
`else
module tb_bnn_benchmark_baseline;
`endif
`ifdef FULL_TEST
    localparam VECTOR_COUNT = 2331;
`elsif EDGE_TEST
    localparam VECTOR_COUNT = 14;
`else
    localparam VECTOR_COUNT = 64;
`endif
`ifdef PIPELINED
    localparam LATENCY = 2;
`else
    localparam LATENCY = 1;
`endif

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;
    reg valid_in = 1'b0;
    reg [39:0] input_features = 40'b0;
    wire valid_out;
    wire fall_detected;
    reg [39:0] vectors [0:VECTOR_COUNT-1];
    reg [0:0] expected [0:VECTOR_COUNT-1];
    integer i;

`ifdef PIPELINED
    bnn_benchmark_pipelined dut (
`else
    bnn_benchmark_baseline dut (
`endif
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .input_features(input_features),
        .valid_out(valid_out), .fall_detected(fall_detected)
    );

    initial begin
`ifdef FULL_TEST
        $readmemh("tb_inputs_full.mem", vectors);
        $readmemh("tb_expected_full.mem", expected);
`elsif EDGE_TEST
        $readmemh("tb_inputs_edge.mem", vectors);
        $readmemh("tb_expected_edge.mem", expected);
`else
        $readmemh("tb_inputs_64.mem", vectors);
        $readmemh("tb_expected_64.mem", expected);
`endif
        // Post-synthesis XSim holds all flip-flops in global reset for 100 ns.
        // Keep the local reset asserted until that interval has passed.
        repeat (12) @(negedge clk);
        rst_n = 1'b1;
        for (i = 0; i < VECTOR_COUNT + LATENCY + 1; i = i + 1) begin
            @(negedge clk);
            valid_in = (i < VECTOR_COUNT);
            input_features = (i < VECTOR_COUNT) ? vectors[i] : 40'b0;
            @(posedge clk);
            #1;
            if (i >= LATENCY && i - LATENCY < VECTOR_COUNT) begin
                if (valid_out !== 1'b1 ||
                    fall_detected !== expected[i-LATENCY][0])
                    $fatal(1, "vector %0d: valid=%b output=%b expected=%b",
                           i-LATENCY, valid_out, fall_detected,
                           expected[i-LATENCY][0]);
            end else if (valid_out !== 1'b0) begin
                $fatal(1, "unexpected valid_out at cycle %0d", i);
            end
        end
`ifdef PIPELINED
        $display("PASS: benchmark pipelined, %0d vectors", VECTOR_COUNT);
`else
        $display("PASS: benchmark baseline, %0d vectors", VECTOR_COUNT);
`endif
        $finish;
    end
endmodule
