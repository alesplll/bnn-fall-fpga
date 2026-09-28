"""Обучение бинарной нейросети на признаках SisFall и сохранение артефактов."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from bnn import BinaryNet, bce_loss
from features import FEATURE_NAMES
from quantize import calibrate

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = ROOT / "artifacts"

SEED = 0
N_HIDDEN = 8
EPOCHS = 300
BATCH_SIZE = 64
LR = 0.05


def load_xy(csv_path: Path):
    df = pd.read_csv(csv_path)
    X = df[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y = df["label"].to_numpy(dtype=np.float64)
    return X, y, df


def accuracy(p: np.ndarray, y: np.ndarray) -> float:
    pred = (p >= 0.5).astype(np.float64)
    return float(np.mean(pred == y))


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    X_train_raw, y_train, _ = load_xy(PROCESSED / "features_train.csv")
    X_test_raw, y_test, _ = load_xy(PROCESSED / "features_test.csv")

    qp = calibrate(X_train_raw)                       # int8 scale, откалиброван ТОЛЬКО по train
    norm_scale = qp.scale * 127.0                        # ~99.5-й процентиль |x| по train
    X_train = X_train_raw / norm_scale                     # ~[-1, 1]
    X_test = X_test_raw / norm_scale

    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    pos_weight = n_neg / max(n_pos, 1.0)
    print(f"train: N={len(y_train)} pos={int(n_pos)} neg={int(n_neg)} pos_weight={pos_weight:.3f}")

    net = BinaryNet(n_in=len(FEATURE_NAMES), n_hidden=N_HIDDEN, seed=SEED)

    history = []
    n = len(y_train)
    for epoch in range(1, EPOCHS + 1):
        order = rng.permutation(n)
        epoch_loss = 0.0
        for start in range(0, n, BATCH_SIZE):
            idx = order[start:start + BATCH_SIZE]
            xb, yb = X_train[idx], y_train[idx]
            sw = np.where(yb == 1, pos_weight, 1.0)
            p, cache = net.forward(xb)
            epoch_loss += bce_loss(p, yb, sw) * len(idx)
            grads = net.backward(cache, yb, sw)
            net.adam_step(grads, lr=LR)
        epoch_loss /= n

        if epoch % 10 == 0 or epoch == 1:
            p_tr, _ = net.forward(X_train)
            p_te, _ = net.forward(X_test)
            acc_tr = accuracy(p_tr, y_train)
            acc_te = accuracy(p_te, y_test)
            history.append(dict(epoch=epoch, loss=epoch_loss, acc_train=acc_tr, acc_test=acc_te))
            print(f"epoch {epoch:4d}  loss={epoch_loss:.4f}  acc_train={acc_tr:.4f}  acc_test={acc_te:.4f}")

    # финальные метрики (float STE-модель, до квантования)
    p_test, _ = net.forward(X_test)
    pred_test = (p_test >= 0.5).astype(int)

    np.savez(
        ARTIFACTS / "model_float.npz",
        W_A=net.W_A, b_A=net.b_A, W_B=net.W_B, b_B=net.b_B,
        norm_scale=norm_scale,
    )
    with open(ARTIFACTS / "quant_params.json", "w") as f:
        json.dump({"feature_names": FEATURE_NAMES,
                    "input_scale": qp.scale.tolist(),
                    "norm_scale": norm_scale.tolist()}, f, indent=2, ensure_ascii=False)
    with open(ARTIFACTS / "train_history.json", "w") as f:
        json.dump(history, f, indent=2)

    pd.DataFrame({"y_true": y_test.astype(int), "p": p_test, "pred": pred_test}).to_csv(
        ARTIFACTS / "test_predictions_float.csv", index=False)

    print("Saved artifacts to", ARTIFACTS)


if __name__ == "__main__":
    main()
