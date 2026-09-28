"""Бинарная нейросеть (BNN) 5 -> 8 -> 1, обучение вручную на NumPy.

Архитектура (см. дизайн практики 1):
  Слой A ("кодировщик", fixed-point):  z = X @ W_A + b_A         (X: 5 признаков)
                                          a = sign(z)  in {-1,+1}^8   <- бинарный код
  Слой B ("классификатор", бинарный): y = a @ sign(W_B) + b_B
                                          class = 1[y >= 0]

Обучение — BinaryConnect / Straight-Through Estimator (Courbariaux et al., 2016):
  - Хранятся вещественные "теневые" веса W_A, W_B.
  - На прямом проходе W_B бинаризуется знаком (веса слоя B),
    активации a тоже бинаризуются знаком.
  - На обратном проходе производная sign(t) заменяется производной
    "hard tanh": d/dt sign(t) ~= 1{|t| <= 1}, иначе 0 (STE).
  - После шага обновления теневые веса W_B клипуются в [-1, 1]
    (классический приём BinaryConnect, иначе веса "убегают" и
    штраф STE перестаёт работать корректно).

Слой A НЕ бинаризуется (его веса после обучения квантуются в int8
пост-фактум в export_vectors.py) - так одна "тяжёлая" по прецизионности
операция (взвешенное суммирование признаков) остаётся fixed-point, а
основная, самая массовая по количеству операций часть (слой-классификатор)
становится настоящей бинарной сетью: XNOR + popcount вместо умножителей.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def sign(x: np.ndarray) -> np.ndarray:
    return np.where(x >= 0, 1.0, -1.0)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


@dataclass
class BinaryNet:
    n_in: int = 5
    n_hidden: int = 8
    seed: int = 0

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.seed)
        self.W_A = rng.normal(0, 1.0 / np.sqrt(self.n_in), size=(self.n_in, self.n_hidden))
        self.b_A = np.zeros(self.n_hidden)
        self.W_B = rng.normal(0, 1.0 / np.sqrt(self.n_hidden), size=(self.n_hidden,))
        self.b_B = 0.0
        self._adam_state: dict = {}

    def forward(self, X: np.ndarray):
        z = X @ self.W_A + self.b_A          # (N, H)
        a = sign(z)                             # (N, H) in {-1,+1}
        Wb = sign(self.W_B)                      # (H,)   in {-1,+1}
        y = a @ Wb + self.b_B                     # (N,)
        p = sigmoid(y)
        cache = dict(X=X, z=z, a=a, Wb=Wb, y=y)
        return p, cache

    def backward(self, cache: dict, label: np.ndarray, sample_weight: np.ndarray | None = None):
        X, z, a, Wb = cache["X"], cache["z"], cache["a"], cache["Wb"]
        N = X.shape[0]
        p = sigmoid(cache["y"])
        w = np.ones(N) if sample_weight is None else sample_weight
        w = w / w.sum()  # нормировка, чтобы масштаб градиента не зависел от размера батча

        dLdy = (p - label) * w                    # (N,)  d(BCE)/dy при y = логит
        dLdb_B = np.sum(dLdy)
        dLdWb = a.T @ dLdy                         # (H,)
        dLdW_B = dLdWb * (np.abs(self.W_B) <= 1.0)   # STE-клип

        dLda = np.outer(dLdy, Wb)                    # (N, H)
        dLdz = dLda * (np.abs(z) <= 1.0)                # STE-клип по предактивации слоя A

        dLdW_A = X.T @ dLdz                              # (n_in, H)
        dLdb_A = np.sum(dLdz, axis=0)

        return dict(W_A=dLdW_A, b_A=dLdb_A, W_B=dLdW_B, b_B=dLdb_B)

    def params(self) -> dict:
        return dict(W_A=self.W_A, b_A=self.b_A, W_B=self.W_B, b_B=self.b_B)

    def set_params(self, p: dict) -> None:
        self.W_A, self.b_A, self.W_B, self.b_B = p["W_A"], p["b_A"], p["W_B"], p["b_B"]

    def adam_step(self, grads: dict, lr: float = 0.05, beta1: float = 0.9,
                  beta2: float = 0.999, eps: float = 1e-8) -> None:
        if not self._adam_state:
            self._adam_state = {
                k: dict(m=np.zeros_like(np.atleast_1d(v), dtype=np.float64),
                        v=np.zeros_like(np.atleast_1d(v), dtype=np.float64), t=0)
                for k, v in self.params().items()
            }
        p = self.params()
        for k in p:
            st = self._adam_state[k]
            st["t"] += 1
            g = np.atleast_1d(grads[k]).astype(np.float64)
            st["m"] = beta1 * st["m"] + (1 - beta1) * g
            st["v"] = beta2 * st["v"] + (1 - beta2) * (g ** 2)
            m_hat = st["m"] / (1 - beta1 ** st["t"])
            v_hat = st["v"] / (1 - beta2 ** st["t"])
            update = lr * m_hat / (np.sqrt(v_hat) + eps)
            new_val = np.asarray(p[k], dtype=np.float64) - update.reshape(np.shape(p[k]) or ())
            p[k] = new_val if np.ndim(p[k]) else float(new_val)
        self.set_params(p)
        # BinaryConnect: теневые веса слоя B клипуются в [-1, 1]
        self.W_B = np.clip(self.W_B, -1.0, 1.0)


def bce_loss(p: np.ndarray, label: np.ndarray, sample_weight: np.ndarray | None = None) -> float:
    eps = 1e-9
    w = np.ones_like(p) if sample_weight is None else sample_weight
    w = w / w.sum()
    losses = -(label * np.log(p + eps) + (1 - label) * np.log(1 - p + eps))
    return float(np.sum(losses * w))
