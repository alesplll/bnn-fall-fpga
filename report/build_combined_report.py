"""Extend the supplied PR1 report with the verified PR2 results."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source_pr1.docx"
OUTPUT = ROOT / "Отчет_ПР1_ПР2_Рябец_Головин_Гришин.docx"
SCREENSHOTS = ROOT / "screenshots"


def replace_text(paragraph, value: str) -> None:
    """Keep the first run's formatting, including the existing title page."""
    if not paragraph.runs:
        paragraph.add_run(value)
        return
    paragraph.runs[0].text = value
    for run in paragraph.runs[1:]:
        run.text = ""


def before(anchor, text: str, style: str):
    paragraph = anchor.insert_paragraph_before(style=style)
    paragraph.add_run(text)
    return paragraph


def toc_before(anchor, text: str, template):
    paragraph = before(anchor, text, "Report Contents")
    paragraph._p.remove(paragraph._p.pPr)
    paragraph._p.insert(0, deepcopy(template._p.pPr))
    return paragraph


def table_before(document, anchor, headers: list[str], rows: list[list[str]], widths: list[float]):
    table = document.add_table(rows=1, cols=len(headers))
    table.autofit = False
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        edge = OxmlElement(f"w:{side}")
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), "4")
        edge.set(qn("w:color"), "000000")
        borders.append(edge)
    table._tbl.tblPr.append(borders)
    for index, title in enumerate(headers):
        table.columns[index].width = Cm(widths[index])
        cell = table.rows[0].cells[index]
        cell.width = Cm(widths[index])
        cell.text = title
        cell.paragraphs[0].style = document.styles["Report Table Text"]
        for run in cell.paragraphs[0].runs:
            run.bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].width = Cm(widths[index])
            cells[index].text = value
            cells[index].paragraphs[0].style = document.styles["Report Table Text"]
    anchor._p.addprevious(table._tbl)
    return table


def evidence_figure(document, filename: str, caption: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(SCREENSHOTS / filename), width=Cm(15.5))
    label = document.add_paragraph(caption, style="Report Body")
    label.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label.paragraph_format.space_after = Pt(12)


def main() -> None:
    doc = Document(SOURCE)
    p = doc.paragraphs

    replace_text(p[8], "ОТЧЁТ ПО ПРАКТИЧЕСКИМ РАБОТАМ № 1–2")
    replace_text(p[11], "Тема: Системная и RTL-модели бинарного нейросетевого классификатора для детектирования падений")
    replace_text(
        p[40],
        "Цель практических работ № 1–2 — построить программную эталонную модель "
        "нейроускорителя, затем разработать её RTL-эквивалент на Verilog и "
        "сверить результаты симуляции с эталонным откликом. В практической "
        "работе № 3 эта RTL-модель станет основой проекта для ПЛИС.",
    )
    before(p[48], "– реализовать целочисленный классификатор 5→8→1 на Verilog с загрузкой весов из .mem-файлов;", "Report Body")
    before(p[48], "– выполнить симуляцию RTL-модели и проверить входы, промежуточные состояния и выходы по эталонным векторам.", "Report Body")

    replace_text(
        p[101],
        "Результаты практической работы № 1, используемые для верификации RTL-модели в практической работе № 2, размещены в каталоге weights/ репозитория:",
    )
    replace_text(p[102], "– weights/golden_vectors_full.csv — полный тестовый набор из 2331 вектора: квантованные входы, восьмибитный код слоя A, сумма слоя B и выход;")
    replace_text(p[103], "– weights/tb_inputs_64.mem и weights/tb_expected_64.mem — 64 отобранных пары «вход — эталонный выход» для начальной симуляции;")
    replace_text(p[104], "– weights/weights_layerA_W.mem, weights_layerA_b.mem, weights_layerB_W.mem, weights_layerB_b.mem — квантованные веса и смещения для $readmemh;")
    replace_text(p[105], "– weights/README.md — точный порядок байт, битов и строк в экспортированных файлах.")
    replace_text(p[121], "Полный исходный код программной модели находится в каталоге model/src/ репозитория. Ниже приведены фрагменты, определяющие вычислительную часть работы.")

    # The source document has a static contents page. Page numbers are filled
    # after rendering, while these entries preserve its paragraph style.
    toc_anchor = p[35]
    toc_before(toc_anchor, "6 ПОСТАНОВКА ЗАДАЧИ ПРАКТИЧЕСКОЙ РАБОТЫ № 2\t16", p[34])
    toc_before(toc_anchor, "7 РЕАЛИЗАЦИЯ RTL-МОДЕЛИ\t17", p[34])
    toc_before(toc_anchor, "8 СИМУЛЯЦИЯ И СВЕРКА С ЭТАЛОНОМ\t18", p[34])
    replace_text(p[35], "ЗАКЛЮЧЕНИЕ\t19")
    replace_text(p[36], "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ\t20")
    replace_text(p[37], "ПРИЛОЖЕНИЕ А КЛЮЧЕВЫЕ ФРАГМЕНТЫ ПРОГРАММЫ\t21")
    toc_before(p[38], "ПРИЛОЖЕНИЕ Б ФРАГМЕНТЫ RTL-МОДЕЛИ\t26", p[34])
    toc_before(p[38], "ПРИЛОЖЕНИЕ В ПОДТВЕРЖДЕНИЕ ПРОВЕРКИ В VIVADO\t27", p[34])

    anchor = p[109]  # Insert all PR2 material before the original conclusion.
    before(anchor, "6 ПОСТАНОВКА ЗАДАЧИ ПРАКТИЧЕСКОЙ РАБОТЫ № 2", "Report Heading 1")
    before(anchor, "6.1 Цель и границы RTL-модели", "Report Heading 2")
    before(anchor,
           "Требование практической работы № 2 — реализовать на Verilog RTL-модель "
           "нейроускорителя, созданного в первой работе, и методом симуляции "
           "сверить её отклик с программным эталоном. Переносится только "
           "классификатор: пять уже рассчитанных и квантованных признаков "
           "подаются на вход. Поиск пика, вычисление угла, jerk и дисперсии "
           "остаются программной подготовкой данных. Такой же вычислительный "
           "контур выбран для эталонной модели в разделе 3.", "Report Body")
    before(anchor, "6.2 Интерфейс и формат данных", "Report Heading 2")
    before(anchor,
           "Входные признаки передаются одним 40-битным словом "
           "{x0, x1, x2, x3, x4}; каждый байт является знаковым числом int8 "
           "в дополнительном коде. Порядок соответствует файлам weights/. "
           "Результат регистрируется на фронте тактового сигнала при valid_in=1. "
           "Сигнал valid_out показывает, что выходной бит относится к принятому "
           "входу. Сброс rst_n синхронный, активный низким уровнем.", "Report Body")
    before(anchor, "Таблица 6.1 — Интерфейс RTL-классификатора", "Report Table Caption")
    table_before(doc, anchor,
                 ["Сигнал", "Бит", "Назначение"],
                 [["clk", "1", "Тактовый сигнал"],
                  ["rst_n", "1", "Синхронный сброс, активный 0"],
                  ["valid_in", "1", "На входе подготовлено слово признаков"],
                  ["input_features", "40", "Пять знаковых байтов x0…x4"],
                  ["valid_out", "1", "Зарегистрированный ответ действителен"],
                  ["fall_detected", "1", "1 — падение, 0 — обычная активность"]],
                 [3.5, 2.7, 9.3])
    after_table = before(anchor,
           "Для воспроизводимости проект ориентирован на Vivado 2022.2 и "
           "кристалл xc7a100tcsg324-1, указанный для курса. Tcl-сценарий "
           "rtl/create_vivado_project.tcl добавляет Verilog, тестбенч и "
           "файлы памяти в проект. Выбор кристалла не влияет на результаты "
           "поведенческой симуляции.", "Report Body")
    after_table.paragraph_format.space_before = Pt(6)

    before(anchor, "7 РЕАЛИЗАЦИЯ RTL-МОДЕЛИ", "Report Heading 1")
    before(anchor, "7.1 Слой A: знаковое умножение и накопление", "Report Heading 2")
    before(anchor,
           "Восемь нейронов слоя A вычисляют z_h = b_A[h] + Σ_j x_j·W_A[j,h] "
           "для j=0…4. Веса W_A загружаются в порядке j·8+h. Операнды "
           "int8 явно трактуются как знаковые; произведение хранится в 16 битах "
           "и расширяется до 32 бит перед сложением со смещением int32. "
           "Промежуточный бит a_h равен 1 тогда и только тогда, когда z_h≥0. "
           "Нулевой случай включён намеренно: так определён эталон в "
           "model/src/golden_model.py.", "Report Body")
    before(anchor, "7.2 Слой B: XNOR и popcount", "Report Heading 2")
    before(anchor,
           "Восемь бинарных весов W_B сравниваются с битами a_h операцией "
           "XNOR. Четырёхбитный счётчик определяет число совпадений от 0 до 8. "
           "Итоговая сумма вычисляется как y = 2·popcount(XNOR(a,W_B)) − 8 + b_B; "
           "выход fall_detected равен 1 при y≥0. Эта формула бит в бит "
           "соответствует программной модели и не требует вещественной "
           "арифметики во время вывода.", "Report Body")
    before(anchor, "7.3 Регистры, сброс и загрузка параметров", "Report Heading 2")
    before(anchor,
           "Комбинационная часть рассчитывает оба слоя для текущего входа. "
           "На ближайшем фронте clk при valid_in=1 сохраняются выходной бит и "
           "valid_out=1; при отсутствии входа valid_out=0, а последний бит "
           "остаётся неизменным. Синхронный сброс обнуляет оба регистра. "
           "Веса и смещения загружаются из четырёх .mem-файлов через "
           "$readmemh. Их формат и порядок фиксированы в weights/README.md; "
           "переобучение сети для ПР2 не выполняется.", "Report Body")

    before(anchor, "8 СИМУЛЯЦИЯ И СВЕРКА С ЭТАЛОНОМ", "Report Heading 1")
    before(anchor, "8.1 Методика верификации", "Report Heading 2")
    before(anchor,
           "Тестбенч rtl/tb_bnn_classifier.v подаёт вход до фронта clk и "
           "сверяет зарегистрированный выход и valid_out с эталоном. На "
           "полном наборе он сравнивает также a_bits и сумму y, что "
           "локализует ошибки по слоям. Отдельно проверяются сброс и снятие "
           "valid_out. Полные тестовые .mem-файлы строятся из "
           "weights/golden_vectors_full.csv сценарием rtl/gen_full_tb.py.", "Report Body")
    before(anchor,
           "В Icarus Verilog 13.0 проверены 64 исходных, 2331 тестовых и "
           "14 граничных векторов со знаковыми значениями −128 и 127. "
           "Ожидаемый выход — решение программной модели, а не истинная "
           "метка SisFall.", "Report Body")
    before(anchor, "8.2 Результаты", "Report Heading 2")
    before(anchor, "Таблица 8.1 — Результаты поведенческой симуляции", "Report Table Caption")
    table_before(doc, anchor,
                 ["Набор", "Число", "Расхождения по выходу", "Расхождения внутри слоёв"],
                 [["Исходный контрольный", "64", "0", "Промежуточные значения не сравнивались"],
                  ["Полный тестовый", "2331", "0", "0 по a_bits и y"],
                  ["Граничные значения int8", "14", "0", "0 по a_bits и y"],
                  ["Vivado XSim, полный набор", "2331", "0", "0 по a_bits и y"]],
                 [4.0, 2.1, 3.3, 6.1])
    after_table = before(anchor,
           "Например, для x=[14,16,27,2,0] модель и RTL дали "
           "a_bits=10100001, y=−5, fall_detected=0. Во всех наборах "
           "расхождений не обнаружено. Это подтверждает функциональную "
           "эквивалентность RTL целочисленному эталону на проверенных входах.", "Report Body")
    after_table.paragraph_format.space_before = Pt(6)
    before(anchor,
           "В Vivado 2022.2 создан проект bnn_pr2 для xc7a100tcsg324-1. "
           "Поведенческая симуляция XSim завершилась сообщением "
           "PASS: 2331 vectors. Временные диаграммы, результат синтеза и "
           "схема приведены в приложении В. Синтез успешно завершился: "
           "использовано 629 Slice LUT, 2 Slice Register, 45 Bonded IOB "
           "и 1 BUFGCTRL. Оценка ресурсов относится только к синтезу; "
           "размещение, трассировка и анализ таймингов не выполнялись.", "Report Body")

    replace_text(
        p[110],
        "В практических работах № 1–2 создана программная и RTL-модель "
        "бинарного классификатора падений 5→8→1. Программная модель "
        "обучена на признаках SisFall и дала на тестовой выборке 97,0 % "
        "accuracy, 84,5 % precision и 93,6 % recall. RTL-модель повторяет "
        "целочисленный тракт: знаковые int8-умножения, 32-битное накопление, "
        "бинаризацию, XNOR и popcount. В поведенческой симуляции Icarus "
        "Verilog получено полное совпадение с эталоном на 64 контрольных, "
        "2331 тестовых и 14 граничных входах; на полном наборе совпали "
        "также промежуточные состояния обоих слоёв. В Vivado 2022.2 "
        "создан проект для xc7a100tcsg324-1, симуляция XSim прошла "
        "2331 вектор без расхождений, синтез завершился успешно и "
        "получена логическая схема. Таким образом, системная модель и её "
        "функционально проверенный RTL-эквивалент готовы к следующему "
        "этапу работы.",
    )

    source_anchor = p[119]
    before(source_anchor,
           "8. AMD. Vivado Design Suite User Guide: Logic Simulation (UG900), version 2022.2. — URL: https://docs.amd.com/r/2022.2-English/ug900-vivado-logic-simulation/ (дата обращения: 03.10.2026).",
           "Report Source")
    before(source_anchor,
           "9. AMD. Vivado Design Suite User Guide: Synthesis (UG901), version 2022.2. — URL: https://docs.amd.com/r/2022.2-English/ug901-vivado-synthesis/ (дата обращения: 03.10.2026).",
           "Report Source")

    doc.add_paragraph("Приложение Б", style="Report Appendix")
    doc.add_paragraph("Ключевые фрагменты RTL-модели и тестбенча", style="Report Appendix Title")
    doc.add_paragraph(
        "Полные исходники находятся в rtl/bnn_classifier.v и "
        "rtl/tb_bnn_classifier.v. Здесь показаны операции, определяющие "
        "совпадение с эталоном.", style="Report Body")
    doc.add_paragraph("Листинг Б.1 — Знаковое накопление и бинаризация слоя A", style="Report Listing Caption")
    code = doc.add_paragraph(style="Report Code")
    code.add_run(
        "accumulator = $signed(b_a[h]);\n"
        "for (j = 0; j < 5; j = j + 1) begin\n"
        "    product = $signed(input_features[39 - 8*j -: 8])\n"
        "            * $signed(w_a[j*8 + h]);\n"
        "    accumulator = accumulator + {{16{product[15]}}, product};\n"
        "end\n"
        "hidden_bits[h] = (accumulator >= 32'sd0);"
    )
    doc.add_paragraph("Листинг Б.2 — XNOR, popcount и пороговое решение", style="Report Listing Caption")
    code = doc.add_paragraph(style="Report Code")
    code.add_run(
        "for (h = 0; h < 8; h = h + 1)\n"
        "    matching_bits = matching_bits + (hidden_bits[h] ~^ w_b[h]);\n"
        "score = ($signed({28'b0, matching_bits}) <<< 1)\n"
        "      - 32'sd8 + $signed(b_b[0]);\n"
        "prediction_next = (score >= 32'sd0);"
    )
    for run in doc.paragraphs[-1].runs:
        run.font.size = Pt(9)

    doc.add_paragraph("Приложение В", style="Report Appendix")
    doc.add_paragraph("Подтверждение проверки в Vivado 2022.2", style="Report Appendix Title")
    doc.add_paragraph(
        "Снимки экрана получены при запуске проекта bnn_pr2 для "
        "xc7a100tcsg324-1. Они фиксируют состав проекта, результат "
        "поведенческой симуляции, временные диаграммы и синтезированную "
        "схему с отчётом использования ресурсов.", style="Report Body")
    evidence_figure(doc, "vivado_project.jpg", "Рисунок В.1 — Проект bnn_pr2 и целевой кристалл")
    evidence_figure(doc, "vivado_simulation_pass.jpg", "Рисунок В.2 — Успешная симуляция 2331 эталонного вектора")
    evidence_figure(doc, "vivado_waveform.jpg", "Рисунок В.3 — Временные диаграммы входов и выходов RTL-модели")
    evidence_figure(doc, "vivado_synthesized_schematic.jpg", "Рисунок В.4 — Общий вид синтезированной логической схемы")
    evidence_figure(doc, "vivado_utilization.jpg", "Рисунок В.5 — Фрагмент схемы и использование ресурсов после синтеза")

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
