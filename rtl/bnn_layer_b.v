`timescale 1ns / 1ps

// Eight binary activations -> one binary decision.
module bnn_layer_b #(
    parameter W_FILE = "weights_layerB_W.mem",
    parameter B_FILE = "weights_layerB_b.mem"
) (
    input  wire [7:0]         hidden_bits,
    output reg  signed [31:0] score,
    output reg                prediction
);
    reg [0:0]  weights [0:7];
    reg [31:0] biases [0:0];

    initial begin
        $readmemh(W_FILE, weights);
        $readmemh(B_FILE, biases);
    end

    reg [3:0] matching_bits;
    integer h;

    always @* begin
        matching_bits = 4'b0;
        for (h = 0; h < 8; h = h + 1)
            matching_bits = matching_bits + (hidden_bits[h] ~^ weights[h][0]);
        score = ($signed({28'b0, matching_bits}) <<< 1)
              - 32'sd8 + $signed(biases[0]);
        prediction = (score >= 32'sd0);
    end
endmodule
