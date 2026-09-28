# rtl

Здесь будет схема — реализация классификатора на уровне регистровых
передач (Verilog): слой A (MAC, int8 × int8 → int32, sign) и слой B
(XNOR + popcount + порог).

Вход и опора для верификации — файлы из [`/weights`](../weights):
веса в `.mem` (`$readmemh`) и тестовые векторы `tb_inputs_64.mem` /
`tb_expected_64.mem` с ожидаемыми ответами для сверки результатов
симуляции. Формат всех файлов расписан в
[`/weights/README.md`](../weights/README.md).
