`timescale 1ns / 1ps

// Integer inference core for the trained 5 -> 8 -> 1 network.
// The five input bytes are packed as {x0, x1, x2, x3, x4}.
// Set valid_in with input_features before a rising clock edge. The prediction
// and valid_out are registered on that edge and remain stable until the next.
module bnn_classifier #(
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
    // Layout matches weights/README.md: W_A[j*8+h] is feature j,
    // hidden neuron h. Two's-complement bytes and biases are signed.
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

    // 8 signed fixed-point MACs. An 8x8 signed product fits in 16 bits;
    // explicit extension keeps the 32-bit accumulator's sign unambiguous.
    reg signed [15:0] product;
    reg signed [31:0] accumulator;
    reg [7:0] hidden_bits;
    reg [3:0] matching_bits;
    reg signed [31:0] score;
    reg prediction_next;
    integer h;
    integer j;

    always @* begin
        product = 16'sd0;
        accumulator = 32'sd0;
        hidden_bits = 8'b0;
        matching_bits = 4'b0;
        score = 32'sd0;
        prediction_next = 1'b0;

        for (h = 0; h < 8; h = h + 1) begin
            accumulator = $signed(b_a[h]);
            for (j = 0; j < 5; j = j + 1) begin
                product = $signed(input_features[39 - 8*j -: 8])
                        * $signed(w_a[j*8 + h]);
                accumulator = accumulator + {{16{product[15]}}, product};
            end
            // Python golden_model.py uses >= 0, including the zero case.
            hidden_bits[h] = (accumulator >= 32'sd0);
        end

        for (h = 0; h < 8; h = h + 1)
            matching_bits = matching_bits + (hidden_bits[h] ~^ w_b[h]);

        // dot({-1,+1}^8) = 2*popcount(XNOR) - 8.
        score = ($signed({28'b0, matching_bits}) <<< 1)
              - 32'sd8 + $signed(b_b[0]);
        prediction_next = (score >= 32'sd0);
    end

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
