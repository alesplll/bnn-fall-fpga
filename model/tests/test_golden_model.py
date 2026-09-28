"""Проверки корректности эталонной (golden) целочисленной модели.

Запуск: python3 -m pytest model/tests -v   (или просто python3 tests/test_golden_model.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from bnn import BinaryNet  # noqa: E402
from features import FEATURE_NAMES  # noqa: E402
from golden_model import forward_from_raw, quantize_model, xnor_popcount_dot  # noqa: E402
from quantize import calibrate  # noqa: E402

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def test_xnor_popcount_matches_dot_product():
    rng = np.random.default_rng(42)
    for _ in range(2000):
        h = rng.integers(2, 33)
        a_pm1 = rng.choice([-1, 1], size=h)
        w_pm1 = rng.choice([-1, 1], size=h)
        a_bit = (a_pm1 > 0).astype(np.int8)
        w_bit = (w_pm1 > 0).astype(np.int8)
        assert int(xnor_popcount_dot(a_bit, w_bit)) == int(np.dot(a_pm1, w_pm1))


def _load_trained():
    d = np.load(ARTIFACTS / "model_float.npz")
    return d["W_A"], d["b_A"], d["W_B"], float(d["b_B"]), d["norm_scale"]


def test_int8_golden_model_matches_float_model_closely():
    if not (ARTIFACTS / "model_float.npz").exists():
        return  # артефакты обучения ещё не сгенерированы - пропускаем
    W_A, b_A, W_B, b_B, norm_scale = _load_trained()

    train_df = pd.read_csv(PROCESSED / "features_train.csv")
    X_train_raw = train_df[FEATURE_NAMES].to_numpy(dtype=np.float64)
    qp = calibrate(X_train_raw)

    test_df = pd.read_csv(PROCESSED / "features_test.csv")
    X_test_raw = test_df[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y_test = test_df["label"].to_numpy(dtype=int)

    net = BinaryNet()
    net.set_params(dict(W_A=W_A, b_A=b_A, W_B=W_B, b_B=b_B))
    p_float, _ = net.forward(X_test_raw / norm_scale)
    pred_float = (p_float >= 0.5).astype(int)

    gw = quantize_model(W_A, b_A, W_B, b_B, qp.scale)
    _, _, _, _, label_int = forward_from_raw(gw, X_test_raw)

    agreement = float(np.mean(label_int.ravel() == pred_float))
    assert agreement >= 0.99, f"int8 golden model diverged from float model too much: {agreement:.4f}"

    acc_int = float(np.mean(label_int.ravel() == y_test))
    assert acc_int >= 0.90, f"int8 golden model accuracy too low: {acc_int:.4f}"


if __name__ == "__main__":
    test_xnor_popcount_matches_dot_product()
    print("test_xnor_popcount_matches_dot_product: OK")
    test_int8_golden_model_matches_float_model_closely()
    print("test_int8_golden_model_matches_float_model_closely: OK")
