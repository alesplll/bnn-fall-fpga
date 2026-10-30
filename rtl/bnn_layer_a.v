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

    // The bundled weights keep every partial sum within signed 16-bit range.
    reg signed [15:0] product [0:4];
    reg signed [15:0] sum01;
    reg signed [15:0] sum23;
    reg signed [15:0] sum0123;
    reg signed [15:0] sum4bias;
    reg signed [15:0] accumulator;
    integer h;
    integer j;

    always @* begin
        for (j = 0; j < 5; j = j + 1)
            product[j] = 16'sd0;
        sum01 = 16'sd0;
        sum23 = 16'sd0;
        sum0123 = 16'sd0;
        sum4bias = 16'sd0;
        accumulator = 16'sd0;
        hidden_bits = 8'b0;
        for (h = 0; h < 8; h = h + 1) begin
            for (j = 0; j < 5; j = j + 1) begin
                product[j] = $signed(input_features[39 - 8*j -: 8])
                           * $signed(weights[j*8 + h]);
            end
            sum01 = product[0] + product[1];
            sum23 = product[2] + product[3];
            sum0123 = sum01 + sum23;
            sum4bias = product[4] + $signed(biases[h][15:0]);
            accumulator = sum0123 + sum4bias;
            hidden_bits[h] = (accumulator >= 16'sd0);
        end
    end
endmodule
