"""Построение датасета признаков из всего SisFall и разбиение train/test.

Разбиение выполняется ПО ИСПЫТУЕМЫМ (subject-wise split), а не по окнам:
несколько окон одного файла или разных файлов одного человека похожи друг
на друга (почерк движения), поэтому попадание одного субъекта одновременно
в train и test завышало бы точность. Тестовые субъекты полностью исключены
из обучения.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sisfall_io import iter_dataset
from features import extract_samples, FEATURE_NAMES

TEST_SUBJECTS = {"SA20", "SA21", "SA22", "SA23", "SE12", "SE13", "SE14", "SE15"}


def build_feature_table(raw_root: Path) -> pd.DataFrame:
    rows = []
    for rec in iter_dataset(raw_root):
        for s in extract_samples(rec):
            row = {
                "subject": s.subject,
                "code": s.code,
                "trial": s.trial,
                "peak_idx": s.peak_idx,
                "label": s.label,
            }
            row.update(zip(FEATURE_NAMES, s.features))
            rows.append(row)
    return pd.DataFrame(rows)


def split_train_test(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    is_test = df["subject"].isin(TEST_SUBJECTS)
    return df[~is_test].reset_index(drop=True), df[is_test].reset_index(drop=True)


def main() -> None:
    model_dir = Path(__file__).resolve().parent.parent
    root = model_dir / "data" / "raw" / "SisFall_dataset"
    out_dir = model_dir / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = model_dir.parent / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {root} ...")
    df = build_feature_table(root)
    print(f"Total windows: {len(df)}  (falls={df['label'].sum()}, non-falls={(df['label']==0).sum()})")

    train_df, test_df = split_train_test(df)
    print(f"Train: {len(train_df)} windows, {train_df['subject'].nunique()} subjects, "
          f"falls={train_df['label'].sum()}")
    print(f"Test:  {len(test_df)} windows, {test_df['subject'].nunique()} subjects, "
          f"falls={test_df['label'].sum()}")

    df.to_csv(out_dir / "features_all.csv", index=False)
    train_df.to_csv(out_dir / "features_train.csv", index=False)
    test_df.to_csv(out_dir / "features_test.csv", index=False)
    print(f"Saved to {out_dir}")

    # единый файл-дистрибутив датасета (та же таблица + колонка split) для /dataset
    master = df.copy()
    master.insert(1, "split", np.where(master["subject"].isin(TEST_SUBJECTS), "test", "train"))
    master.to_csv(dataset_dir / "sisfall_5features.csv", index=False)
    print(f"Saved master dataset to {dataset_dir / 'sisfall_5features.csv'}")


if __name__ == "__main__":
    main()
