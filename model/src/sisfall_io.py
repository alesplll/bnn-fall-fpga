"""Чтение и разбор сырых файлов датасета SisFall.

Формат файла (см. SisFall_dataset/Readme.txt):
  9 столбцов, строки разделены запятыми, строка завершается ';'.
  1-3: ADXL345 (акселерометр, диапазон +-16g, разрешение 13 бит)
  4-6: ITG3200  (гироскоп,      диапазон +-2000 deg/s, разрешение 16 бит)
  7-9: MMA8451Q (второй акселерометр, не используется в этом проекте)

Перевод "сырых" АЦП-кодов в физические единицы:
  value_phys = (2 * Range / 2**Resolution) * AD
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE_HZ = 200.0

ADXL345_RANGE_G = 16.0
ADXL345_RESOLUTION_BITS = 13
ITG3200_RANGE_DPS = 2000.0
ITG3200_RESOLUTION_BITS = 16

ACC_SCALE = (2.0 * ADXL345_RANGE_G) / (2 ** ADXL345_RESOLUTION_BITS)   # g / LSB
GYRO_SCALE = (2.0 * ITG3200_RANGE_DPS) / (2 ** ITG3200_RESOLUTION_BITS)  # deg/s / LSB

FILENAME_RE = re.compile(r"^(?P<code>[DF]\d{2})_(?P<subject>S[AE]\d{2})_(?P<trial>R\d{2})\.txt$")

FALL_CODES = {f"F{i:02d}" for i in range(1, 16)}
ADL_CODES = {f"D{i:02d}" for i in range(1, 20)}


@dataclass(frozen=True)
class Recording:
    path: Path
    code: str          # e.g. "F05" or "D12"
    subject: str        # e.g. "SA01"
    trial: str           # e.g. "R04"
    is_fall: bool
    acc_g: np.ndarray     # (N, 3) float64, [g], columns X,Y,Z (ADXL345)
    gyro_dps: np.ndarray   # (N, 3) float64, [deg/s], columns X,Y,Z (ITG3200)

    @property
    def n_samples(self) -> int:
        return self.acc_g.shape[0]

    @property
    def duration_s(self) -> float:
        return self.n_samples / SAMPLE_RATE_HZ


def parse_filename(path: Path) -> tuple[str, str, str]:
    m = FILENAME_RE.match(path.name)
    if not m:
        raise ValueError(f"Unexpected SisFall filename: {path.name}")
    return m.group("code"), m.group("subject"), m.group("trial")


def load_recording(path: Path) -> Recording:
    code, subject, trial = parse_filename(path)
    raw_text = path.read_text().replace(";", "")
    raw = np.genfromtxt(raw_text.splitlines(), delimiter=",", dtype=np.float64)
    if raw.ndim == 1:
        raw = raw.reshape(1, -1)
    if raw.shape[1] != 9:
        raise ValueError(f"{path}: expected 9 columns, got {raw.shape[1]}")

    acc_g = raw[:, 0:3] * ACC_SCALE
    gyro_dps = raw[:, 3:6] * GYRO_SCALE

    return Recording(
        path=path,
        code=code,
        subject=subject,
        trial=trial,
        is_fall=code in FALL_CODES,
        acc_g=acc_g,
        gyro_dps=gyro_dps,
    )


def iter_dataset(root: Path):
    """Итератор по всем .txt-записям датасета (в порядке обхода директорий)."""
    root = Path(root)
    for subject_dir in sorted(root.iterdir()):
        if not subject_dir.is_dir():
            continue
        for txt_path in sorted(subject_dir.glob("*.txt")):
            yield load_recording(txt_path)
