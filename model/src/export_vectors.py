"""Экспорт обученных весов и эталонного отклика в /weights.

Формирует набор файлов, которые непосредственно переиспользуются
аппаратной частью проекта (RTL / ПЛИС):
  weights/golden_vectors_full.csv   - весь тестовый набор (вход, промежуточные
                                       сигналы, выход) для прослеживаемости
  weights/tb_inputs_64.mem            - 64 входных вектора (5 x int8, hex,
                                         $readmemh) для тестбенча Verilog
  weights/tb_expected_64.mem           - ожидаемые метки для тех же 64 векторов
  weights/weights_layerA_W.mem          - веса слоя A, int8, hex, $readmemh
  weights/weights_layerA_b.mem           - смещения слоя A, int32, hex
  weights/weights_layerB_W.mem            - веса слоя B, 1 бит (0/1), hex
  weights/weights_layerB_b.mem             - порог слоя B, int32, hex
  weights/README.md                         - описание форматов
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from features import FEATURE_NAMES
from golden_model import forward_from_raw, quantize_model
from quantize import calibrate

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = ROOT / "artifacts"
WEIGHTS = REPO_ROOT / "weights"

N_SAMPLE_VECTORS = 64
SEED = 0


def to_hex_twos_complement(value: int, n_bits: int) -> str:
    mask = (1 << n_bits) - 1
    return format(int(value) & mask, f"0{n_bits // 4}x")


def write_mem(path: Path, lines: list[str], header: str) -> None:
    with open(path, "w") as f:
        f.write(f"// {header}\n")
        for line in lines:
            f.write(line + "\n")


def main() -> None:
    WEIGHTS.mkdir(parents=True, exist_ok=True)

    d = np.load(ARTIFACTS / "model_float.npz")
    W_A, b_A, W_B, b_B = d["W_A"], d["b_A"], d["W_B"], float(d["b_B"])

    train_df = pd.read_csv(PROCESSED / "features_train.csv")
    qp = calibrate(train_df[FEATURE_NAMES].to_numpy(dtype=np.float64))
    gw = quantize_model(W_A, b_A, W_B, b_B, qp.scale)

    test_df = pd.read_csv(PROCESSED / "features_test.csv")
    X_raw = test_df[FEATURE_NAMES].to_numpy(dtype=np.float64)
    X_i8, z_i32, a_bit, y_i32, label = forward_from_raw(gw, X_raw)

    full = test_df[["subject", "code", "trial", "label"]].copy()
    for i, name in enumerate(FEATURE_NAMES):
        full[f"x_raw_{name}"] = X_raw[:, i]
        full[f"x_i8_{i}"] = X_i8[:, i]
    full["a_bits"] = ["".join(str(b) for b in row[::-1]) for row in a_bit]
    full["y_i32"] = y_i32
    full["pred_label"] = label.ravel()
    full.to_csv(WEIGHTS / "golden_vectors_full.csv", index=False)
    print(f"Full golden reference: {len(full)} vectors -> golden_vectors_full.csv")

    rng = np.random.default_rng(SEED)
    idx_pos = np.where(test_df["label"].to_numpy() == 1)[0]
    idx_neg = np.where(test_df["label"].to_numpy() == 0)[0]
    k = N_SAMPLE_VECTORS // 2
    sel = np.sort(np.concatenate([
        rng.choice(idx_pos, size=min(k, len(idx_pos)), replace=False),
        rng.choice(idx_neg, size=min(k, len(idx_neg)), replace=False),
    ]))

    input_lines, expected_lines = [], []
    for i in sel:
        byte_str = "".join(to_hex_twos_complement(int(X_i8[i, j]), 8) for j in range(5))
        input_lines.append(byte_str)
        expected_lines.append(format(int(label[i]), "01x"))

    write_mem(WEIGHTS / "tb_inputs_64.mem", input_lines,
              "64 golden-теста, каждая строка = 5 x int8 (X0..X4), 40 бит, hex, big-endian по индексу признака")
    write_mem(WEIGHTS / "tb_expected_64.mem", expected_lines,
              "Ожидаемая метка (0/1) для соответствующей строки tb_inputs_64.mem")

    W_A_lines = [to_hex_twos_complement(int(gw.W_A_i8[j, h]), 8)
                 for j in range(gw.n_in) for h in range(gw.n_hidden)]
    write_mem(WEIGHTS / "weights_layerA_W.mem", W_A_lines,
              f"W_A int8, порядок: j=0..{gw.n_in - 1} (внешний), h=0..{gw.n_hidden - 1} (внутренний). "
              f"{gw.n_in * gw.n_hidden} строк")

    b_A_lines = [to_hex_twos_complement(int(v), 32) for v in gw.b_A_i32]
    write_mem(WEIGHTS / "weights_layerA_b.mem", b_A_lines, "b_A int32, по одному на нейрон h=0..H-1")

    W_B_lines = [format(int(v), "01x") for v in gw.W_B_bit]
    write_mem(WEIGHTS / "weights_layerB_W.mem", W_B_lines,
              "W_B бит: 1 <=> вес +1, 0 <=> вес -1, по одному на нейрон h=0..H-1")

    write_mem(WEIGHTS / "weights_layerB_b.mem", [to_hex_twos_complement(gw.b_B_i32, 32)],
              "b_B int32 (порог слоя-классификатора)")

    in_scale_lines = [f"{s:.10f}" for s in gw.in_scale]
    (WEIGHTS / "input_scale.txt").write_text(
        "# масштаб квантования входа per-feature: x_i8 = round(x_raw / scale)\n"
        + "\n".join(f"{name}: {s}" for name, s in zip(FEATURE_NAMES, in_scale_lines))
        + f"\nw_scale_A: {gw.w_scale_A:.10f}\n"
    )

    layout = f"""# Формат файлов в /weights

Точка передачи данных из модели в аппаратную часть проекта. Архитектура:
5 входов (int8) -> слой A (Linear int8, {gw.n_in}x{gw.n_hidden} + bias int32,
sign) -> {gw.n_hidden}-битный код -> слой B (XNOR-popcount, {gw.n_hidden}x1 бинарные веса
+ порог int32, sign) -> 1 бит (0 = не падение, 1 = падение).

## tb_inputs_64.mem / tb_expected_64.mem
64 репрезентативных теста из тестовой выборки (32 падения + 32 не-падения,
детерминированная выборка, seed={SEED}). Каждая строка tb_inputs_64.mem -
40-битное hex-число: конкатенация X0 X1 X2 X3 X4 (каждый int8 в
дополнительном коде, 2 hex-цифры, признаки в порядке {FEATURE_NAMES}).
Соответствующая строка tb_expected_64.mem - ожидаемый выходной бит.
Полный тестовый набор (2331 вектор) с промежуточными сигналами - в
golden_vectors_full.csv (там же a_bits - эталонный 8-битный код после
слоя A, для пошаговой верификации).

## weights_layerA_W.mem ({gw.n_in * gw.n_hidden} строк)
W_A[j,h], int8 доп. код, порядок: j (признак) - внешний цикл, h (нейрон) -
внутренний, т.е. строка k = j*{gw.n_hidden} + h.

## weights_layerA_b.mem ({gw.n_hidden} строк)
b_A[h], int32 доп. код, аккумулятор z[h] = sum_j(X_i8[j]*W_A[j,h]) + b_A[h].

## weights_layerB_W.mem / weights_layerB_b.mem
W_B[h] в виде 1 бита (1<=>+1, 0<=>-1), сумма by XNOR+popcount:
  y = 2*popcount(XNOR(a_bits, W_B_bit)) - {gw.n_hidden} + b_B
  label = (y >= 0)

## input_scale.txt
Масштаб квантования признаков (нужен, если фичи будут пересчитываться
на лету, а не браться из golden-набора).

Код, который сгенерировал эти файлы: model/src/export_vectors.py
(запускается после model/src/train.py).
"""
    (WEIGHTS / "README.md").write_text(layout)

    print(f"weights written to {WEIGHTS}")
    print(f"Selected {len(sel)} vectors: {len(idx_pos[:k])} falls + {len(idx_neg[:k])} non-falls (from seed pool)")


if __name__ == "__main__":
    main()
