# Практическая работа № 2 — RTL-модель

`bnn_classifier.v` повторяет целочисленный эталон из
`model/src/golden_model.py`. Вход — пять уже квантованных `int8` признаков
в 40-битном слове `{x0,x1,x2,x3,x4}`. Выход — один бит: `1` означает падение.
При `valid_in=1` на фронте `clk` защёлкиваются `fall_detected` и `valid_out`.
При `valid_in=0` выходной бит сохраняется, а `valid_out` сбрасывается.
Активный низкий `rst_n` синхронно сбрасывает оба выхода.

Слой A: для каждого из восьми нейронов сумма пяти знаковых произведений
`int8 × int8` и смещения `int32`; бит активации равен `1` при сумме `>= 0`.
Слой B: XNOR каждого бита активации с бинарным весом, popcount, затем
`score = 2*popcount - 8 + b_B`; падение при `score >= 0`. Форматы весов и
тестов приведены в [`weights/README.md`](../weights/README.md).
Расчёт пяти признаков из сигналов датчиков остаётся в Python и не входит
в RTL-модель.

## Проверка в Icarus Verilog

Запускать из `weights/`: `$readmemh` читает файлы по именам из рабочего
каталога. Каждая команда компилирует RTL и тестбенч, затем запускает
симуляцию. Код выхода ненулевой при любой ошибке.

```bash
cd weights
iverilog -g2012 -s tb_bnn_classifier -o /tmp/bnn_pr2_64 ../rtl/bnn_classifier.v ../rtl/tb_bnn_classifier.v
vvp /tmp/bnn_pr2_64
iverilog -g2012 -DFULL_TEST -s tb_bnn_classifier -o /tmp/bnn_pr2_full ../rtl/bnn_classifier.v ../rtl/tb_bnn_classifier.v
vvp /tmp/bnn_pr2_full
iverilog -g2012 -DEDGE_TEST -s tb_bnn_classifier -o /tmp/bnn_pr2_edge ../rtl/bnn_classifier.v ../rtl/tb_bnn_classifier.v
vvp /tmp/bnn_pr2_edge
```

Режим по умолчанию проверяет 64 подготовленных в ПР1 примера. `FULL_TEST`
проверяет все 2331 тестовых примеров, включая промежуточные биты слоя A и
сумму слоя B. `EDGE_TEST` проверяет 14 дополнительных комбинаций с
`-128`, `127`, нулём и смешанными знаками. Полные и граничные `.mem` файлы
воспроизводятся командой `python rtl/gen_full_tb.py` из корня репозитория.
Ожидаемый бит в этих файлах — ответ программной модели, а не метка
разметки SisFall: симуляция проверяет эквивалентность RTL и эталона.

## Проект Vivado 2022.2

Проверенный результат: XSim завершил полный тест из 2331 вектора с
сообщением `PASS: 2331 vectors`; **Run Synthesis** завершился успешно.
В **Open Synthesized Design → Schematic** доступна схема классификатора,
а в **Report Utilization** — оценка ресурсов: 629 Slice LUT,
2 Slice Register, 45 Bonded IOB и 1 BUFGCTRL. Это результаты синтеза;
размещение и проверка на плате не проводились.

На Windows распакуйте репозиторий в каталог с коротким путём из английских
букв, цифр и подчёркиваний, например `C:\npu_pr2\bnn_fall_fpga`. Из корня
репозитория запустите:

```bat
vivado.bat -mode batch -source rtl/create_vivado_project.tcl
```

Сценарий создаёт `vivado_pr2/bnn_pr2.xpr`, добавляет Verilog, тестбенч и
все `.mem` файлы, выбирает полный тест из 2331 векторов. Откройте проект
в Vivado и выполните **Run Behavioral Simulation**. В консоли ожидается
`PASS: 2331 vectors`. Для проверки 64 примеров удалите `FULL_TEST` из
свойства `verilog_define` у `sim_1`; для граничных примеров укажите
`EDGE_TEST`.

Чтобы увидеть временные диаграммы, добавьте сигналы `clk`, `rst_n`,
`valid_in`, `input_features`, `valid_out`, `fall_detected` в окно Waveform,
выполните `restart`, затем `run 200 ns` и настройте масштаб времени.
Для схемы выполните **Run Synthesis**, затем **Open Synthesized Design →
Schematic**; сводка ресурсов открывается через **Report Utilization**.

По умолчанию проект использует `xc7a100tcsg324-1`, указанный для курса.
При работе с другим кристаллом задайте переменную окружения `FPGA_PART`
перед запуском сценария.
