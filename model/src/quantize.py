"""Fixed-point (int8) квантование признаков и весов.

Симметричное квантование без нулевой точки (zero-point = 0):
    q = clip(round(x / scale), -128, 127)
    x_hat = q * scale

Масштаб (scale) калибруется по обучающей выборке отдельно для каждого из
5 признаков (у них разный физический диапазон: g, градусы, deg/s, g/s, g^2),
и отдельно для весов каждого слоя. Порог берётся по 99.5-му процентилю
модуля значения, а не по максимуму, чтобы редкие выбросы не съедали
динамический диапазон 8 бит.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

INT8_MIN, INT8_MAX = -128, 127
CALIBRATION_PERCENTILE = 99.5


@dataclass
class QuantParams:
    scale: np.ndarray  # (n,) float64, один масштаб на столбец/канал

    def quantize(self, x: np.ndarray) -> np.ndarray:
        q = np.round(x / self.scale)
        return np.clip(q, INT8_MIN, INT8_MAX).astype(np.int8)

    def dequantize(self, q: np.ndarray) -> np.ndarray:
        return q.astype(np.float64) * self.scale


def calibrate(x: np.ndarray, percentile: float = CALIBRATION_PERCENTILE) -> QuantParams:
    """x: (N, C). Возвращает по одному масштабу на каждый из C столбцов."""
    x = np.atleast_2d(x)
    abs_max = np.percentile(np.abs(x), percentile, axis=0)
    abs_max = np.maximum(abs_max, 1e-8)
    scale = abs_max / INT8_MAX
    return QuantParams(scale=scale)
