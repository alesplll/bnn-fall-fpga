"""Извлечение 5 признаков падения из одной записи SisFall.

Признаки (см. постановку задачи проекта):
  1. peak_acc_g      - модуль результирующего ускорения в момент пика, g
  2. tilt_deg         - угол наклона тела относительно опорной (начальной) ориентации
                        в момент пика, градусы
  3. peak_gyro_dps     - модуль угловой скорости в окрестности пика, deg/s
  4. jerk_g_per_s       - максимальная по модулю скорость изменения ускорения
                          (производная |a|) в окрестности пика, g/s
  5. post_peak_var_g2    - дисперсия результирующего ускорения на коротком окне
                           ПОСЛЕ пика (0.5-1.5с) - отличает "лежит неподвижно"
                           (настоящее падение) от резкого движения без падения.

Один "образец" = одно окно анализа вокруг одного локального пика ускорения.
Для коротких испытаний (сидение/падение/лежание, 12-25с) на файл берётся
одно окно (весь файл). Для длинных ADL (ходьба/бег, 100с) файл нарезается
на несколько скользящих окон, чтобы не терять разнообразие "нормальной"
активности.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sisfall_io import SAMPLE_RATE_HZ, Recording

FS = SAMPLE_RATE_HZ
WINDOW_S = 4.0
WINDOW_N = int(WINDOW_S * FS)          # 800 samples
LONG_TRIAL_CODES = {"D01", "D02", "D03", "D04"}  # 100s непрерывные ADL - нарезаем
STRIDE_S = 2.0
STRIDE_N = int(STRIDE_S * FS)           # 400 samples

GYRO_NEIGHBORHOOD_S = 0.5
JERK_NEIGHBORHOOD_S = 0.25
POST_PEAK_START_S = 0.5
POST_PEAK_END_S = 1.5
MIN_POST_PEAK_SAMPLES = 40             # минимум отсчётов для оценки дисперсии
CALIBRATION_S = 0.5                     # опорная (начальная) ориентация тела

FEATURE_NAMES = [
    "peak_acc_g",
    "tilt_deg",
    "peak_gyro_dps",
    "jerk_g_per_s",
    "post_peak_var_g2",
]


@dataclass(frozen=True)
class FeatureSample:
    features: np.ndarray  # shape (5,), float64
    label: int              # 1 = падение, 0 = обычная активность
    subject: str
    code: str
    trial: str
    peak_idx: int


def _resultant(vec3: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum(vec3 ** 2, axis=1))


def _extract_one_window(rec: Recording, res_acc: np.ndarray, res_gyro: np.ndarray,
                         ref_vec: np.ndarray, search_lo: int, search_hi: int) -> FeatureSample | None:
    n = rec.n_samples
    search_hi = min(search_hi, n)
    if search_hi - search_lo < 10:
        return None

    local_peak = int(np.argmax(res_acc[search_lo:search_hi]))
    peak_idx = search_lo + local_peak

    peak_acc_g = float(res_acc[peak_idx])

    a_peak = rec.acc_g[peak_idx]
    cos_theta = np.dot(a_peak, ref_vec) / (np.linalg.norm(a_peak) * np.linalg.norm(ref_vec) + 1e-9)
    tilt_deg = float(np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0))))

    gyro_nb = int(GYRO_NEIGHBORHOOD_S * FS)
    g_lo, g_hi = max(0, peak_idx - gyro_nb), min(n, peak_idx + gyro_nb)
    peak_gyro_dps = float(np.max(res_gyro[g_lo:g_hi]))

    jerk_nb = int(JERK_NEIGHBORHOOD_S * FS)
    j_lo, j_hi = max(1, peak_idx - jerk_nb), min(n, peak_idx + jerk_nb)
    if j_hi - j_lo < 2:
        jerk_g_per_s = 0.0
    else:
        jerk_series = np.abs(np.diff(res_acc[j_lo - 1:j_hi])) * FS
        jerk_g_per_s = float(np.max(jerk_series))

    p_lo = peak_idx + int(POST_PEAK_START_S * FS)
    p_hi = peak_idx + int(POST_PEAK_END_S * FS)
    p_hi = min(p_hi, n)
    if p_hi - p_lo < MIN_POST_PEAK_SAMPLES:
        return None
    post_peak_var_g2 = float(np.var(res_acc[p_lo:p_hi]))

    features = np.array([peak_acc_g, tilt_deg, peak_gyro_dps, jerk_g_per_s, post_peak_var_g2])
    return FeatureSample(
        features=features,
        label=int(rec.is_fall),
        subject=rec.subject,
        code=rec.code,
        trial=rec.trial,
        peak_idx=peak_idx,
    )


def extract_samples(rec: Recording) -> list[FeatureSample]:
    n = rec.n_samples
    res_acc = _resultant(rec.acc_g)
    res_gyro = _resultant(rec.gyro_dps)
    calib_n = max(1, min(n, int(CALIBRATION_S * FS)))
    ref_vec = np.mean(rec.acc_g[:calib_n], axis=0)
    if np.linalg.norm(ref_vec) < 1e-6:
        ref_vec = np.array([0.0, 0.0, 1.0])

    samples: list[FeatureSample] = []
    if rec.code in LONG_TRIAL_CODES:
        start = 0
        while start < n:
            hi = min(start + WINDOW_N, n)
            s = _extract_one_window(rec, res_acc, res_gyro, ref_vec, start, hi)
            if s is not None:
                samples.append(s)
            if hi >= n:
                break
            start += STRIDE_N
    else:
        s = _extract_one_window(rec, res_acc, res_gyro, ref_vec, 0, n)
        if s is not None:
            samples.append(s)
    return samples
