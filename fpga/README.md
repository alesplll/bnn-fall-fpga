# Практическая работа № 3 — прототип на ПЛИС

`fpga_top.v` подключает неизменённый классификатор из ПР2 к небольшому
встроенному контрольному набору: 64 входа и 64 ожидаемых ответа из ПР1.
После импульса `start` модуль по одному подаёт векторы на классификатор,
сверяет ответы и выставляет `done`, `pass`, `checked_count` и `error_count`.
Сигнал `last_prediction` показывает последний ответ. Повторный импульс
`start` запускает проверку заново. Отладочная плата для этой схемы не
указана, поэтому физические выводы не назначаются.

## Локальная проверка логики

Из каталога `weights/`:

```bash
iverilog -g2012 -s tb_fpga_top -o /tmp/bnn_pr3_tb ../rtl/bnn_classifier.v ../fpga/fpga_top.v ../fpga/tb_fpga_top.v
vvp /tmp/bnn_pr3_tb
```

Тестбенч проверяет три запуска: совпадение всех 64 векторов,
обнаружение одной специально внесённой ошибки и повторный успешный
прогон после восстановления эталона.

## Vivado 2022.2 на Windows

В уже открытом Vivado откройте **Window → Tcl Console** и выполните:

```tcl
cd D:/neuroproc/bnn-fall-fpga
source fpga/run_implementation.tcl
```

Либо из командной строки в корне репозитория вызовите `vivado.bat`
через его полный путь из каталога `Vivado/2022.2/bin`:

```bat
"C:\path\to\Vivado\2022.2\bin\vivado.bat" -mode batch -source fpga/run_implementation.tcl -log vivado_pr3.log -journal vivado_pr3.jou
```

Сценарий создаёт `vivado_pr3/bnn_pr3.xpr` под кристалл
`xc7a100tcsg324-1`, выполняет синтез, размещение и трассировку,
сохраняет отчёты и контрольную точку в `vivado_pr3/reports/`.
Для просмотра проекта откройте `.xpr` в Vivado, запустите **Run Behavioral
Simulation** и убедитесь, что в консоли есть сообщение
`PASS: FPGA prototype self-test; 64 vectors, error detection and restart`.
Для схемы и размещения используйте **Open Implemented Design**.

Для оформления отчёта сохраните из Vivado:

1. Скрин **Tcl Console** с `PR3_SYNTHESIS_STATUS`,
   `PR3_IMPLEMENTATION_STATUS` и `PR3_DONE`.
2. Скрин симуляции с сообщением `PASS` и временной диаграммой сигналов
   `clk`, `start`, `busy`, `done`, `pass`, `checked_count`, `error_count`.
3. Скрин **Open Implemented Design → Device** с размещением и
   скрин **Schematic** верхнего модуля.
4. Файлы `vivado_pr3/reports/utilization_routed.rpt`,
   `timing_routed.rpt`, `route_status.rpt` и `drc_routed.rpt`.
   По ним определяются ресурсы, результат трассировки, WNS и ограничения
   анализа; один лишь статус завершения не подтверждает выполнения
   временного ограничения.

`clock_only.xdc` задаёт период 20 нс (условная цель 50 МГц) только для
анализа таймингов. Назначений выводов и битового потока нет: без модели
отладочной платы и её схемы подключения их нельзя обоснованно задать.
Запуск сценария в Vivado и результаты его отчётов должны быть проверены
на Windows; локальный запуск Verilog этого не заменяет.
