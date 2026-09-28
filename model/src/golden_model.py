"""Эталонная (golden) модель: точная целочисленная реализация forward pass.

Это "системная модель нейроускорителя" в смысле методички - именно её
выход считается эталонным откликом, с которым в практике 2 будет сверяться
RTL-модель методом симуляции. Здесь НЕТ ни одного float: только int8/int32
арифметика для слоя A и XNOR+popcount для слоя B, то есть ровно то, что
предстоит повторить в Verilog.

Квантование (симметричное, per-tensor):
  X_i8[j]      = round(x_raw[j] / in_scale[j])                       (5,)   int8
  W_A_i8[j,h]  = round(W_A_float[j,h] / w_scale_A)                    (5,8)  int8
  b_A_i32[h]   = round(b_A_float[h] / (w_scale_A / 127))               (8,)   int32

  z_i32[h] = sum_j X_i8[j] * W_A_i8[j,h] + b_A_i32[h]
  a_bit[h] = 1 if z_i32[h] >= 0 else 0        # бинарный код слоя A (1 бит/нейрон)

  W_B_bit[h]  in {0,1}, 1 <=> вес +1, 0 <=> вес -1
  y_i32 = sum_h XNOR(a_bit[h], W_B_bit[h])*2 - H  + b_B_i32   (H = n_hidden)
        = dot(a_pm1, W_B_pm1) + b_B_i32
  label = 1 if y_i32 >= 0 else 0

XNOR+popcount тождество: для a,w in {-1,+1}^H
    dot(a, w) = 2*popcount(XNOR(a_bits, w_bits)) - H
(a_bits[h]=1 <=> a[h]=+1; аналогично для w). Проверяется тестом
tests/test_golden_matches_python.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quantize import QuantParams, INT8_MIN, INT8_MAX


@dataclass
class GoldenWeights:
    in_scale: np.ndarray      # (5,)  float, масштаб квантования входа (per-feature)
    W_A_i8: np.ndarray          # (5, H) int8
    b_A_i32: np.ndarray          # (H,)  int32
    w_scale_A: float               # скаляр, масштаб квантования весов слоя A
    W_B_bit: np.ndarray             # (H,)  {0,1}: 1 <=> вес +1
    b_B_i32: int                     # целочисленный порог слоя B

    @property
    def n_in(self) -> int:
        return self.W_A_i8.shape[0]

    @property
    def n_hidden(self) -> int:
        return self.W_A_i8.shape[1]


def quantize_model(W_A: np.ndarray, b_A: np.ndarray, W_B: np.ndarray, b_B: float,
                    in_scale: np.ndarray) -> GoldenWeights:
    w_scale_A = max(float(np.max(np.abs(W_A))) / INT8_MAX, 1e-8)
    W_A_i8 = np.clip(np.round(W_A / w_scale_A), INT8_MIN, INT8_MAX).astype(np.int32)
    b_A_i32 = np.round(b_A / (w_scale_A / INT8_MAX)).astype(np.int64)

    W_B_sign = np.where(W_B >= 0, 1, -1)
    W_B_bit = (W_B_sign > 0).astype(np.int8)
    b_B_i32 = int(np.round(b_B))

    return GoldenWeights(
        in_scale=in_scale.astype(np.float64),
        W_A_i8=W_A_i8.astype(np.int32),
        b_A_i32=b_A_i32.astype(np.int64),
        w_scale_A=w_scale_A,
        W_B_bit=W_B_bit,
        b_B_i32=b_B_i32,
    )


def quantize_input(x_raw: np.ndarray, in_scale: np.ndarray) -> np.ndarray:
    q = np.round(x_raw / in_scale)
    return np.clip(q, INT8_MIN, INT8_MAX).astype(np.int32)


def xnor_popcount_dot(a_bit: np.ndarray, w_bit: np.ndarray) -> np.ndarray:
    """dot(a_pm1, w_pm1) через XNOR + popcount, a_bit/w_bit in {0,1}."""
    xnor = 1 - (a_bit ^ w_bit)              # 1, если биты совпали (оба +1 или оба -1)
    H = w_bit.shape[-1]
    popcount = np.sum(xnor, axis=-1)
    return 2 * popcount - H


def forward_int(gw: GoldenWeights, X_i8: np.ndarray):
    """X_i8: (N, n_in) int. Возвращает (z_i32, a_bit, y_i32, label)."""
    X_i8 = np.atleast_2d(X_i8).astype(np.int64)
    z_i32 = X_i8 @ gw.W_A_i8.astype(np.int64) + gw.b_A_i32   # (N, H)
    a_bit = (z_i32 >= 0).astype(np.int8)                        # (N, H)

    y_i32 = xnor_popcount_dot(a_bit, np.broadcast_to(gw.W_B_bit, a_bit.shape)) + gw.b_B_i32
    label = (y_i32 >= 0).astype(np.int32)
    return z_i32, a_bit, y_i32, label


def forward_from_raw(gw: GoldenWeights, X_raw: np.ndarray):
    X_i8 = quantize_input(np.atleast_2d(X_raw), gw.in_scale)
    return (X_i8,) + forward_int(gw, X_i8)
