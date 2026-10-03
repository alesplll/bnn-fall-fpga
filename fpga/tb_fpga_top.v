`timescale 1ns / 1ps

module tb_fpga_top;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg rst_n = 1'b0;
    reg start = 1'b0;
    wire busy;
    wire done;
    wire pass;
    wire [6:0] checked_count;
    wire [6:0] error_count;
    wire last_prediction;
    reg saved_expected;
    integer cycles;

    fpga_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .busy(busy),
        .done(done),
        .pass(pass),
        .checked_count(checked_count),
        .error_count(error_count),
        .last_prediction(last_prediction)
    );

    task run_once;
        input [6:0] wanted_errors;
        begin
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            if (busy !== 1'b1 || done !== 1'b0)
                $fatal(1, "start did not begin a new run");

            cycles = 0;
            while (done !== 1'b1 && cycles < 140) begin
                @(posedge clk);
                #1;
                cycles = cycles + 1;
            end
            if (done !== 1'b1)
                $fatal(1, "prototype did not finish");
            if (busy !== 1'b0 || checked_count !== 7'd64 ||
                error_count !== wanted_errors ||
                pass !== (wanted_errors == 7'd0))
                $fatal(1, "wrong result: checked=%0d errors=%0d pass=%b",
                       checked_count, error_count, pass);
        end
    endtask

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        run_once(7'd0);

        // Corrupt one expected bit to check the error counter and pass flag.
        saved_expected = dut.expected[3];
        dut.expected[3] = ~saved_expected;
        run_once(7'd1);
        dut.expected[3] = saved_expected;
        run_once(7'd0);

        $display("PASS: FPGA prototype self-test; 64 vectors, error detection and restart");
        $finish;
    end
endmodule
