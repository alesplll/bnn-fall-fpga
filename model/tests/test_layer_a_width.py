"""Ensure the bundled weights are safe for the layer A 16-bit adder tree."""

from pathlib import Path


WEIGHTS = Path(__file__).resolve().parents[2] / "weights"


def _signed(hex_value: str, bits: int) -> int:
    value = int(hex_value, 16)
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def test_layer_a_partial_sums_fit_signed_16_bits():
    weights = [_signed(x, 8) for x in (WEIGHTS / "weights_layerA_W.mem").read_text().split()]
    biases = [_signed(x, 32) for x in (WEIGHTS / "weights_layerA_b.mem").read_text().split()]
    assert len(weights) == 40 and len(biases) == 8

    for neuron, bias in enumerate(biases):
        w = [weights[feature * 8 + neuron] for feature in range(5)]
        for indices, offset in ((range(2), 0), ((2, 3), 0), (range(4), 0), ((4,), bias), (range(5), bias)):
            minimum = offset + sum(min(-128 * w[i], 127 * w[i]) for i in indices)
            maximum = offset + sum(max(-128 * w[i], 127 * w[i]) for i in indices)
            assert -32768 <= minimum <= maximum <= 32767


if __name__ == "__main__":
    test_layer_a_partial_sums_fit_signed_16_bits()
    print("PASS: layer A partial sums fit signed 16 bits")
