"""Extend the verified PR1–PR2 report with the measured PR3 prototype results."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.shared import Pt

from build_combined_report import (
    before,
    evidence_figure_before,
    replace_text,
    table_before,
    toc_before,
)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "Отчет_ПР1_ПР2_Рябец_Головин_Гришин.docx"
OUTPUT = ROOT / "Отчет_ПР1_ПР2_ПР3_Рябец_Головин_Гришин.docx"
EVIDENCE = ROOT / "evidence" / "pr3"
FPGA = ROOT.parent / "fpga"


def field(filename: str, pattern: str) -> str:
    content = (EVIDENCE / filename).read_text(encoding="utf-8")
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise ValueError(f"Missing expected result in {filename}: {pattern}")
    return match.group(1)


def source_without_comments(filename: str) -> str:
    lines = (FPGA / filename).read_text(encoding="utf-8").splitlines()
    return "\n".join(
        line for line in lines
        if not line.lstrip().startswith(("//", "#"))
    ).strip()


def main() -> None:
    lut = field("utilization_routed.rpt", r"\| Slice LUTs\s+\|\s+(\d+)")
    registers = field("utilization_routed.rpt", r"\| Slice Registers\s+\|\s+(\d+)")
    slices = field("utilization_routed.rpt", r"\| Slice\s+\|\s+(\d+)")
    iob = field("utilization_routed.rpt", r"\| Bonded IOB\s+\|\s+(\d+)")
    bufg = field("utilization_routed.rpt", r"\| BUFGCTRL\s+\|\s+(\d+)")
    bram = field("utilization_routed.rpt", r"\| Block RAM Tile\s+\|\s+(\d+)")
    dsp = field("utilization_routed.rpt", r"\| DSPs\s+\|\s+(\d+)")
    routed = field("route_status.rpt", r"# of fully routed nets\.+\s*:\s*(\d+)")
    routable = field("route_status.rpt", r"# of routable nets\.+\s*:\s*(\d+)")
    routing_errors = field("route_status.rpt", r"# of nets with routing errors\.+\s*:\s*(\d+)")
    wns = field("timing_routed.rpt", r"^\s*([\d.]+)\s+0\.000\s+0\s+53\s+[\d.]+\s+0\.000")
    whs = field("timing_routed.rpt", r"^\s*[\d.]+\s+0\.000\s+0\s+53\s+([\d.]+)\s+0\.000")
    no_input_delay = field("timing_routed.rpt", r"There are (\d+) input ports with no input delay specified")
    no_output_delay = field("timing_routed.rpt", r"There are (\d+) ports with no output delay specified")
    drc_violations = field("drc_routed.rpt", r"Violations found:\s*(\d+)")
    if routed != routable or routing_errors != "0":
        raise ValueError("Route report does not confirm complete error-free routing")

    doc = Document(SOURCE)
    p = doc.paragraphs
    replace_text(p[8], "ОТЧЁТ ПО ПРАКТИЧЕСКИМ РАБОТАМ № 1–3")
    replace_text(
        p[11],
        "Тема: Программная модель, RTL-модель и прототип нейросетевого классификатора падений на ПЛИС",
    )
    replace_text(
        p[44],
        "Цель практических работ № 1–3 — построить программную эталонную "
        "модель нейроускорителя, разработать её RTL-эквивалент на Verilog, "
        "проверить совпадение вычислений в симуляции и реализовать прототип "
        "классификатора для выбранного кристалла ПЛИС. Модель обрабатывает "
        "подготовленные признаки движения и выдаёт один бит решения.",
    )
    before(
        p[54],
        "– создать верхний модуль прототипа с контрольным набором, проверить "
        "его работу симуляцией и выполнить размещение и трассировку в Vivado;",
        "Report Body",
    )
    before(
        p[54],
        "– оценить использование ресурсов, результат трассировки и временные "
        "характеристики для выбранного кристалла.",
        "Report Body",
    )

    toc_before(p[38], "9 ПРОТОТИП НА ПЛИС\t21", p[37])
    toc_before(p[38], "10 СИМУЛЯЦИЯ И РЕЗУЛЬТАТЫ РЕАЛИЗАЦИИ\t24", p[37])
    replace_text(p[38], "ЗАКЛЮЧЕНИЕ\t26")
    replace_text(p[39], "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ\t27")
    replace_text(p[40], "ПРИЛОЖЕНИЕ А КЛЮЧЕВЫЕ ФРАГМЕНТЫ ПРОГРАММЫ\t28")
    replace_text(p[41], "ПРИЛОЖЕНИЕ Б ИСХОДНЫЙ КОД RTL-МОДЕЛИ\t33")
    toc_before(p[42], "ПРИЛОЖЕНИЕ В КОД ПРОТОТИПА И ОГРАНИЧЕНИЕ\t36", p[41])

    anchor = p[149]
    before(anchor, "9 ПРОТОТИП НА ПЛИС", "Report Heading 1")
    before(anchor, "9.1 Состав прототипа и интерфейс", "Report Heading 2")
    before(
        anchor,
        "Верхний модуль fpga_top соединяет неизменённый RTL-классификатор "
        "с постоянным набором из 64 входных слов и 64 ожидаемых ответов. "
        "Набор включает 32 примера падения и 32 примера обычной активности. "
        "Входы и эталонные биты загружаются в память при инициализации. "
        "После импульса start автомат последовательно подаёт каждый вектор "
        "на классификатор и сверяет зарегистрированный ответ с эталоном. "
        "На один вектор приходятся два такта: подача и проверка. После "
        "последней проверки устанавливаются done и pass, а счётчики "
        "checked_count и error_count показывают объём проверки и число "
        "расхождений. Повторный импульс start начинает новый прогон.",
        "Report Body",
    )
    before(anchor, "Таблица 9.1 — Внешние сигналы прототипа", "Report Table Caption")
    table_before(
        doc,
        anchor,
        ["Сигнал", "Разрядность", "Назначение"],
        [
            ["clk, rst_n", "1 + 1", "Тактирование и синхронный сброс"],
            ["start", "1", "Импульс запуска контрольного прогона"],
            ["busy, done, pass", "1 + 1 + 1", "Ход, завершение и результат проверки"],
            ["checked_count, error_count", "7 + 7", "Число проверенных векторов и расхождений"],
            ["last_prediction", "1", "Последний ответ классификатора"],
        ],
        [5.0, 2.8, 7.7],
    )
    before(
        anchor,
        "Структура реализованного верхнего уровня приведена на рисунке 9.1. "
        "Внутри него находится тот же вычислительный тракт 5→8→1, который "
        "проверен в практической работе № 2; дополнительная логика выполняет "
        "подачу контрольных данных и самопроверку.",
        "Report Body",
    )
    evidence_figure_before(anchor, "vivado_pr3_schematic.jpg", "Рисунок 9.1 — Логическая схема верхнего уровня после реализации")

    before(anchor, "9.2 Ограничения и физическая реализация", "Report Heading 2")
    before(
        anchor,
        "Проект bnn_pr3 реализован в Vivado 2022.2 для Artix-7 "
        "xc7a100tcsg324-1. Ограничение create_clock задаёт период 20 нс "
        "(расчётную частоту 50 МГц). После синтеза выполнены оптимизация, "
        "размещение и трассировка. Окно Device с размещёнными элементами "
        "показано на рисунке 9.2. Это результат реализации для выбранного "
        "кристалла; физические контакты конкретной отладочной платы не "
        "назначались.",
        "Report Body",
    )
    evidence_figure_before(anchor, "vivado_pr3_device_full.jpg", "Рисунок 9.2 — Размещение прототипа на кристалле в Vivado")
    before(
        anchor,
        f"Отчёт маршрутизации зафиксировал {routable} трассируемых цепей; "
        f"все {routed} проложены, ошибок маршрутизации {routing_errors}. "
        "Таким образом, логические соединения схемы физически проложены "
        "средствами Vivado. Итоговый статус синтеза и реализации показан "
        "на рисунке 9.3.",
        "Report Body",
    )
    evidence_figure_before(anchor, "vivado_pr3_statuses.jpg", "Рисунок 9.3 — Завершение синтеза и реализации в Vivado")

    before(anchor, "10 СИМУЛЯЦИЯ И РЕЗУЛЬТАТЫ РЕАЛИЗАЦИИ", "Report Heading 1")
    before(anchor, "10.1 Проверка работы верхнего модуля", "Report Heading 2")
    before(
        anchor,
        "В XSim выполнена поведенческая симуляция самопроверяющегося "
        "тестбенча tb_fpga_top. Первый запуск подтвердил совпадение "
        "всех 64 ответов с эталоном. Затем один ожидаемый бит был "
        "намеренно изменён: прототип зафиксировал одно расхождение и "
        "снял флаг pass. После восстановления эталона повторный запуск "
        "снова завершился без ошибок. Консоль XSim вывела сообщение "
        "PASS: FPGA prototype self-test; 64 vectors, error detection and restart "
        "(рисунок 10.1). Такая проверка подтверждает работу автомата "
        "подачи векторов, счётчиков и механизма обнаружения ошибок в симуляции.",
        "Report Body",
    )
    evidence_figure_before(anchor, "vivado_pr3_simulation_pass.jpg", "Рисунок 10.1 — Результат симуляции верхнего модуля в XSim")

    before(anchor, "10.2 Ресурсы, трассировка и временные характеристики", "Report Heading 2")
    before(anchor, "Таблица 10.1 — Использование ресурсов после трассировки", "Report Table Caption")
    table_before(
        doc,
        anchor,
        ["Ресурс", "Использовано", "Доля доступных ресурсов"],
        [
            ["Slice LUT", lut, "1,02 %"],
            ["Slice Register", registers, "0,02 %"],
            ["Slice", slices, "1,32 %"],
            ["Bonded IOB", iob, "10,00 %"],
            ["BUFGCTRL", bufg, "3,13 %"],
        ],
        [5.6, 3.5, 6.4],
    )
    before(
        anchor,
        "Ресурсы относятся к верхнему модулю с автоматом самопроверки и "
        "встроенным контрольным набором; их нельзя напрямую сопоставлять "
        "с оценкой отдельного классификатора после синтеза в разделе 8. "
        "Память контрольных данных и весов оптимизирована в логические "
        f"ресурсы; блоков BRAM использовано {bram}, блоков DSP — {dsp}.",
        "Report Body",
    )
    before(anchor, "Таблица 10.2 — Результаты трассировки и анализа таймингов", "Report Table Caption")
    table_before(
        doc,
        anchor,
        ["Показатель", "Значение", "Смысл"],
        [
            ["Трассируемые / проложенные цепи", f"{routable} / {routed}", "Все трассируемые цепи проложены"],
            ["Ошибки маршрутизации", routing_errors, "Ошибок нет"],
            ["Период clk", "20,000 нс", "Расчётная цель 50 МГц"],
            ["WNS / TNS", f"+{wns.replace('.', ',')} нс / 0 нс", "Нарушений setup нет"],
            ["WHS / THS", f"+{whs.replace('.', ',')} нс / 0 нс", "Нарушений hold нет"],
        ],
        [5.8, 3.0, 6.7],
    )
    before(
        anchor,
        "Для внутренних синхронных путей ограничение 20 нс соблюдено: "
        f"худший запас времени установки составляет +{wns.replace('.', ',')} нс, "
        "суммарное нарушение равно нулю. Худший запас времени удержания "
        f"составляет +{whs.replace('.', ',')} нс. Наиболее длинный путь идёт от регистра "
        "индекса контрольного вектора к регистру решения классификатора; "
        "его задержка данных составляет 14,675 нс, в том числе 9,371 нс "
        "приходится на соединения. Оценка относится к данной реализации "
        "и заданному периоду, а не к произвольной отладочной плате.",
        "Report Body",
    )

    before(anchor, "10.3 Границы проверки", "Report Heading 2")
    before(
        anchor,
        f"У {no_input_delay} входов и {no_output_delay} выходов не заданы "
        "внешние задержки; приведённый вывод о выполнении таймингов "
        "относится к внутренним синхронным путям. В отчёте DRC отмечены "
        f"{drc_violations} нарушения: NSTD-1, UCIO-1 и CFGBVS-1. "
        "Причина — отсутствие выбранной отладочной платы и сведений о "
        "её распиновке, стандартах ввода-вывода и напряжении конфигурации. "
        "Поэтому битовый поток не генерировался и проверка на плате не "
        "проводилась. Подтверждены симуляция и физическая реализация "
        "в Vivado для выбранного кристалла.",
        "Report Body",
    )

    replace_text(
        p[150],
        "В практических работах № 1–3 построена программная модель "
        "бинарного классификатора падений 5→8→1, разработана её "
        "целочисленная RTL-реализация и создан прототип для ПЛИС. "
        "Программная модель дала на тестовой выборке 97,0 % accuracy, "
        "84,5 % precision и 93,6 % recall. RTL-классификатор совпал с "
        "целочисленным эталоном на 2331 проверенном векторе. "
        "Самопроверяющийся прототип успешно прошёл три сценария XSim "
        "с набором из 64 векторов. В Vivado 2022.2 для Artix-7 "
        "xc7a100tcsg324-1 выполнены размещение и трассировка: "
        f"проложены все {routed} трассируемых цепей, ошибок маршрутизации "
        f"нет, WNS при периоде 20 нс равен +{wns.replace('.', ',')} нс. "
        "Результат подтверждает реализуемость вычислительного тракта "
        "на выбранном кристалле. Назначение выводов, генерация битового "
        "потока и испытание на плате не выполнялись.",
    )

    source_anchor = p[161]
    before(
        source_anchor,
        "10. AMD. Vivado Design Suite User Guide: Implementation (UG904), version 2022.2. — URL: https://docs.amd.com/r/2022.2-English/ug904-vivado-implementation/ (дата обращения: 03.10.2026).",
        "Report Source",
    )

    doc.add_paragraph("Приложение В", style="Report Appendix")
    doc.add_paragraph("Код прототипа и ограничение тактового сигнала", style="Report Appendix Title")
    doc.add_paragraph(
        "Приведены полные тексты верхнего модуля, его тестбенча и "
        "временного ограничения. Комментарии опущены.",
        style="Report Body",
    )
    for number, filename, title in (
        ("В.1", "fpga_top.v", "Верхний модуль прототипа"),
        ("В.2", "tb_fpga_top.v", "Тестбенч прототипа"),
        ("В.3", "clock_only.xdc", "Ограничение тактового сигнала"),
    ):
        doc.add_paragraph(f"Листинг {number} — {title}", style="Report Listing Caption")
        paragraph = doc.add_paragraph(style="Report Code")
        run = paragraph.add_run(source_without_comments(filename))
        run.font.size = Pt(9)

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
