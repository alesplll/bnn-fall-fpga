"""Convert the committed golden CSV into exhaustive $readmemh test vectors."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WEIGHTS = ROOT / "weights"


def write_mem(name: str, values: list[int], bits: int) -> None:
    mask = (1 << bits) - 1
    width = bits // 4
    with (WEIGHTS / name).open("w", encoding="ascii") as file:
        file.write(f"// {len(values)} golden vectors, {bits} bits each\n")
        file.writelines(f"{value & mask:0{width}x}\n" for value in values)


def read_signed_mem(name: str, bits: int) -> list[int]:
    values = []
    for line in (WEIGHTS / name).read_text(encoding="utf-8").splitlines():
        if line.startswith("//") or not line:
            continue
        value = int(line, 16)
        values.append(value - (1 << bits) if value & (1 << (bits - 1)) else value)
    return values


def pack_features(features: list[int]) -> int:
    assert len(features) == 5 and all(-128 <= x <= 127 for x in features)
    return sum((x & 0xFF) << (8 * (4 - j)) for j, x in enumerate(features))


def export_edge_cases() -> None:
    """Exercise signed-byte boundaries, including values absent from SisFall."""
    w_a = read_signed_mem("weights_layerA_W.mem", 8)
    b_a = read_signed_mem("weights_layerA_b.mem", 32)
    w_b = read_signed_mem("weights_layerB_W.mem", 2)
    b_b = read_signed_mem("weights_layerB_b.mem", 32)
    assert len(w_a) == 40 and len(b_a) == 8 and len(w_b) == 8 and len(b_b) == 1

    cases = [[0] * 5, [-128] * 5, [127] * 5, [-128, 127, -1, 1, 0]]
    for j in range(5):
        case = [0] * 5
        case[j] = -128
        cases.append(case)
    for j in range(5):
        case = [0] * 5
        case[j] = 127
        cases.append(case)

    inputs, labels, hidden, scores = [], [], [], []
    for x in cases:
        a = [int(sum(x[j] * w_a[j * 8 + h] for j in range(5)) + b_a[h] >= 0)
             for h in range(8)]
        score = 2 * sum(a[h] == w_b[h] for h in range(8)) - 8 + b_b[0]
        inputs.append(pack_features(x))
        hidden.append(sum(bit << h for h, bit in enumerate(a)))
        scores.append(score)
        labels.append(int(score >= 0))

    write_mem("tb_inputs_edge.mem", inputs, 40)
    write_mem("tb_expected_edge.mem", labels, 4)
    write_mem("tb_hidden_edge.mem", hidden, 8)
    write_mem("tb_score_edge.mem", scores, 32)
    assert len(inputs) == 14


def main() -> None:
    inputs: list[int] = []
    labels: list[int] = []
    hidden: list[int] = []
    scores: list[int] = []

    with (WEIGHTS / "golden_vectors_full.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            features = [int(row[f"x_i8_{j}"]) for j in range(5)]
            inputs.append(pack_features(features))

            bits = row["a_bits"]
            assert len(bits) == 8 and set(bits) <= {"0", "1"}
            hidden.append(int(bits, 2))

            score = int(row["y_i32"])
            label = int(row["pred_label"])
            assert -(1 << 31) <= score < (1 << 31)
            assert label == int(score >= 0)
            scores.append(score)
            labels.append(label)

    assert len(inputs) == 2331, f"unexpected golden dataset size: {len(inputs)}"
    write_mem("tb_inputs_full.mem", inputs, 40)
    write_mem("tb_expected_full.mem", labels, 4)
    write_mem("tb_hidden_full.mem", hidden, 8)
    write_mem("tb_score_full.mem", scores, 32)
    export_edge_cases()
    print(f"Exported {len(inputs)} complete golden vectors and 14 signed edge cases")


if __name__ == "__main__":
    main()
