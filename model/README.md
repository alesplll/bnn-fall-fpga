# model

Код модели: от сырых данных инерциальных датчиков до обученного
бинарного классификатора и его точной целочисленной реализации.

## Структура

```
data/
  raw/SisFall_dataset/     сырые данные (скачивается отдельно, в git не хранится)
  processed/                 извлечённые признаки (csv)
src/
  sisfall_io.py               парсинг сырых файлов SisFall -> физические единицы
  features.py                  извлечение 5 признаков (окно + поиск пика)
  dataset.py                    обход датасета, subject-wise train/test split
  quantize.py                    симметричное int8-квантование
  bnn.py                          BNN 5->8->1, обучение (BinaryConnect/STE) на NumPy
  train.py                         обучение, сохранение весов
  golden_model.py                   целочисленная (int8/XNOR+popcount) эталонная модель
  evaluate.py                        метрики, графики
  export_vectors.py                   экспорт обученных весов и тестовых векторов в /weights
artifacts/                            результаты обучения: веса (model_float.npz), метрики,
                                       кривая обучения, графики (plots/)
tests/                                  корректность целочисленной модели (XNOR-popcount,
                                         int8 vs float)
```

## Датасет

Используется открытый датасет **SisFall** (акселерометр + гироскоп,
200 Гц, 38 испытуемых, размеченные падения и повседневная активность).
Официальный сайт проекта недоступен — архив берём из зеркала:
[github.com/BIng2325/SisFall](https://github.com/BIng2325/SisFall/releases)
(`SisFall.zip` -> внутри `SisFall_dataset.zip`, распаковать в
`data/raw/SisFall_dataset/`).

## Пять признаков

Модуль результирующего ускорения, угол наклона тела относительно
начальной ориентации, модуль угловой скорости, jerk (скорость
изменения ускорения) и дисперсия ускорения в короткое окно после
пика — всё считается вокруг локального пика ускорения в каждой
записи (см. `src/features.py`).

## Архитектура

Бинарная нейросеть 5 → 8 → 1: первый слой — fixed-point (int8 веса,
int32 аккумулятор), второй — истинно бинарный (веса ∈ {-1,+1},
реализуется как XNOR + popcount вместо умножения). Подробности и
формулы квантования — в `src/golden_model.py` и `src/quantize.py`.

## Запуск

```bash
python3 -m venv .venv && source .venv/bin/activate   # опционально
pip install -r requirements.txt

cd src
python3 dataset.py          # сырые файлы -> ../data/processed/features_*.csv
python3 train.py               # обучение BNN -> ../artifacts/model_float.npz
python3 evaluate.py               # метрики + графики -> ../artifacts/
python3 export_vectors.py            # обученные веса + тестовые векторы -> ../../weights/

cd .. && python3 tests/test_golden_model.py
```

## Результаты (тестовая выборка, 8 испытуемых, не участвовавших в обучении)

int8-модель: accuracy 97.0 %, precision 84.5 %, recall 93.6 %.
Совпадение с вещественной моделью до квантования — 99.9 % решений.
