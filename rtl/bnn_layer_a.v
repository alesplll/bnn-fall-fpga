`timescale 1ns / 1ps

// Five signed int8 features -> eight thresholded hidden neurons.
module bnn_layer_a #(
    parameter W_FILE = "weights_layerA_W.mem",
    parameter B_FILE = "weights_layerA_b.mem"
) (
    input  wire [39:0] input_features,
    output reg  [7:0]  hidden_bits
);
    reg [7:0]  weights [0:39];
    reg [31:0] biases [0:7];

    initial begin
        $readmemh(W_FILE, weights);
        $readmemh(B_FILE, biases);
    end

    reg signed [15:0] product;
    reg signed [31:0] accumulator;
    integer h;
    integer j;

    always @* begin
        product = 16'sd0;
        accumulator = 32'sd0;
        hidden_bits = 8'b0;
        for (h = 0; h < 8; h = h + 1) begin
            accumulator = $signed(biases[h]);
            for (j = 0; j < 5; j = j + 1) begin
                product = $signed(input_features[39 - 8*j -: 8])
                        * $signed(weights[j*8 + h]);
                accumulator = accumulator + {{16{product[15]}}, product};
            end
            hidden_bits[h] = (accumulator >= 32'sd0);
        end
    end
endmodule
