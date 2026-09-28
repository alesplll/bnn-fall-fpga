"""Оценка качества модели (float STE и int8 golden) + графики для отчёта."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bnn import BinaryNet
from features import FEATURE_NAMES
from golden_model import forward_from_raw, quantize_model
from quantize import calibrate

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = ROOT / "artifacts"
PLOTS = ARTIFACTS / "plots"

RU_FEATURE_LABELS = {
    "peak_acc_g": "Пиковое ускорение, g",
    "tilt_deg": "Угол наклона, °",
    "peak_gyro_dps": "Пиковая угл. скорость, °/с",
    "jerk_g_per_s": "Jerk, g/с",
    "post_peak_var_g2": "Дисперсия после пика, g²",
}


def confusion(y_true: np.ndarray, y_pred: np.ndarray):
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return tp, tn, fp, fn


def metrics_from_confusion(tp, tn, fp, fn):
    acc = (tp + tn) / max(tp + tn + fp + fn, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    return dict(accuracy=acc, precision=precision, recall=recall, f1=f1,
                tp=tp, tn=tn, fp=fp, fn=fn)


def plot_confusion(cm: dict, title: str, out_path: Path):
    mat = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
    fig, ax = plt.subplots(figsize=(4, 4))
    im = ax.imshow(mat, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(mat[i, j]), ha="center", va="center",
                     color="white" if mat[i, j] > mat.max() / 2 else "black", fontsize=14)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Не падение", "Падение"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Не падение", "Падение"])
    ax.set_xlabel("Предсказание"); ax.set_ylabel("Истина")
    ax.set_title(title)
    fig.colorbar(im, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_training_curve(history: list[dict], out_path: Path):
    epochs = [h["epoch"] for h in history]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.5))
    ax1.plot(epochs, [h["loss"] for h in history])
    ax1.set_xlabel("Эпоха"); ax1.set_ylabel("BCE loss"); ax1.set_title("Функция потерь")
    ax2.plot(epochs, [h["acc_train"] for h in history], label="train")
    ax2.plot(epochs, [h["acc_test"] for h in history], label="test")
    ax2.set_xlabel("Эпоха"); ax2.set_ylabel("Accuracy"); ax2.set_title("Точность")
    ax2.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_feature_distributions(df: pd.DataFrame, out_path: Path):
    fig, axes = plt.subplots(1, 5, figsize=(18, 3.5))
    for ax, feat in zip(axes, FEATURE_NAMES):
        data0 = df.loc[df["label"] == 0, feat]
        data1 = df.loc[df["label"] == 1, feat]
        ax.boxplot([data0, data1], tick_labels=["не падение", "падение"], showfliers=False)
        ax.set_title(RU_FEATURE_LABELS[feat], fontsize=10)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)

    d = np.load(ARTIFACTS / "model_float.npz")
    W_A, b_A, W_B, b_B, norm_scale = d["W_A"], d["b_A"], d["W_B"], float(d["b_B"]), d["norm_scale"]

    train_df = pd.read_csv(PROCESSED / "features_train.csv")
    test_df = pd.read_csv(PROCESSED / "features_test.csv")
    X_train_raw = train_df[FEATURE_NAMES].to_numpy(dtype=np.float64)
    X_test_raw = test_df[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y_test = test_df["label"].to_numpy(dtype=int)

    qp = calibrate(X_train_raw)

    net = BinaryNet()
    net.set_params(dict(W_A=W_A, b_A=b_A, W_B=W_B, b_B=b_B))
    p_float, _ = net.forward(X_test_raw / norm_scale)
    pred_float = (p_float >= 0.5).astype(int)

    gw = quantize_model(W_A, b_A, W_B, b_B, qp.scale)
    _, _, _, _, label_int = forward_from_raw(gw, X_test_raw)
    pred_int = label_int.ravel()

    cm_float = metrics_from_confusion(*confusion(y_test, pred_float))
    cm_int = metrics_from_confusion(*confusion(y_test, pred_int))
    agreement = float(np.mean(pred_float == pred_int))

    results = {
        "test_set": {"n": int(len(y_test)), "n_falls": int(y_test.sum()),
                       "n_non_falls": int(len(y_test) - y_test.sum())},
        "float_model": cm_float,
        "int8_golden_model": cm_int,
        "float_vs_int8_agreement": agreement,
    }
    with open(ARTIFACTS / "metrics.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    plot_confusion(cm_float, "Матрица ошибок (float-модель)", PLOTS / "confusion_float.png")
    plot_confusion(cm_int, "Матрица ошибок (int8 golden-модель)", PLOTS / "confusion_int8.png")

    with open(ARTIFACTS / "train_history.json") as f:
        history = json.load(f)
    plot_training_curve(history, PLOTS / "training_curve.png")

    all_df = pd.read_csv(PROCESSED / "features_all.csv")
    plot_feature_distributions(all_df, PLOTS / "feature_distributions.png")

    print("Plots saved to", PLOTS)


if __name__ == "__main__":
    main()
