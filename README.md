# depviz — граф зависимостей Maven-пакетов

Только стандартная библиотека Python 3.8+. Для PNG нужна утилита `d2` (https://d2lang.com).

## Запуск
```
python main.py --config config.csv --stage 1   # параметры (key: value)
python main.py --config config.csv --stage 2   # прямые зависимости
python main.py --config config.csv --stage 3   # граф: BFS, глубина, фильтр, циклы
python main.py --config config.csv --stage 4   # порядок загрузки
python main.py --config config.csv --stage 5   # D2 + PNG (по умолчанию)
```
Тестовый режим: `--config config_test.csv` (файл `test_repo.txt`, формат `A: B C`).

## config.csv
`ключ,значение`, по строке на параметр, `#` — комментарий:
package_name (`group:artifact:version`), repo_url, test_mode (true/false),
output_file (*.png), max_depth (>=0), filter_substring (может быть пустым).

## Сравнение с реальным Maven (для отчёта)
- Этап 4: `mvn dependency:tree` и `mvn dependency:build-classpath`.
- Этап 5: `mvn dependency:tree -DoutputType=dot` или `-Dverbose`.
- Возможные расхождения: Maven разрешает конфликты версий («ближайшее определение
  побеждает»), а здесь каждая версия — отдельная вершина; Maven учитывает exclusions,
  BOM-импорты (scope import) и диапазоны версий (здесь берётся нижняя граница);
  граф здесь показывает дубликаты и циклы, дерево Maven — нет.

## Коммиты
```
git commit -m "feat(stage1): add CSV config and CLI parameter validation"
git commit -m "feat(stage2): fetch direct Maven dependencies from pom.xml"
git commit -m "feat(stage3): build dependency graph with recursive BFS, depth and filter"
git commit -m "feat(stage4): add dependency load order"
git commit -m "feat(stage5): generate D2 diagram and PNG"
```
