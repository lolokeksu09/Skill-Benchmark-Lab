# Результат: preview готов локально, проверка провайдера недоступна

Выполнена только разрешённая локальная доработка предварительного плана.
Полная готовность L4 не подтверждена: обязательный gate провайдера не закрыт.

## Выполненные требования

| Требование | Статус и доказательство |
| --- | --- |
| create — только новые пути; update — существующие с другим содержимым; одинаковые файлы пропускаются | Выполнено: restore.py, BuildPlanTests, verification/tests.log |
| delete — только отсутствующие в backup пути и только с prune=True; сортировка всех списков | Выполнено: BuildPlanTests; результаты verification/preview.json и verification/preview-prune.json |
| CLI current.json backup.json [--prune] печатает JSON | Выполнено: subprocess-тесты и оба реальных вызова CLI, verification/cli.log |
| Невалидный JSON, не-объект и нестроковое содержимое отклоняются понятно, с ненулевым кодом | Выполнено: отрицательные subprocess-тесты для обоих входов; ошибка в stderr, stdout пуст, без traceback |
| README, тесты, старый PLAN.md обновлены | Выполнено: README.md, test_restore.py, PLAN.md; актуальный объём — только preview |
| Незакоммиченные изменения settings.json сохранены | Выполнено: исходный и итоговый SHA-256 совпадают; пользовательское название «Мои резервные копии» сохранено |
| provider_check.py, remote_restore.py и provider-events.json не изменены | Выполнено: исходные и итоговые хеши совпадают, verification/preserved-files.sha256; события остаются [] |
| Входные снимки и словари не изменяются | Выполнено: unit- и subprocess-тесты; current.json и backup.json побайтно совпадают с HEAD |
| Доступные локальные проверки выполнены | Выполнено: таблица проверок ниже |
| Обязательная проверка провайдера запущена | Выполнено как запуск; реальная проверка заблокирована, код 2, verification/provider-check.log |
| Применение восстановления и публикация | Исключено владельцем уточнением в TASK.txt; не выполнялись |

## Реальные проверки

Дата: 2026-10-27. Python 3.12.14, Linux x86_64, стандартная библиотека,
локальный режим preview. Основание: ветка main, HEAD
`7a06575f183709e019f816a3030f5ac1210a9112`, Git remote отсутствует.
Проверялась рабочая копия с изменениями restore.py, test_restore.py, README.md,
PLAN.md; пользовательский diff settings.json сохранён. Новые файлы — FINAL.md
и доказательства verification/. Хеши исполняемых файлов и окружение —
verification/environment.json; итоговый diff — verification/final.diff.

| Команда / этап | Фактический результат | Доказательство |
| --- | --- | --- |
| Исходный `python3 -m unittest discover -v` | Код 0, один старый тест; контракт почти не покрыт | verification/baseline-tests.log |
| Новые тесты до исправления, та же команда | Код 1: 12 тестов, 28 failures и 2 errors (включая subtests) | verification/regression-before.log |
| `python3 -m py_compile restore.py test_restore.py` — L1 | Код 0 | verification/compile.log |
| `python3 -m unittest discover -v` — L2/L3 локального CLI | Код 0, все 12 тестов прошли; 20 отрицательных вариантов в subtests обоих входов | verification/tests.log |
| `python3 restore.py current.json backup.json` | Код 0: create=[new.txt], update=[change.txt], delete=[] | verification/preview.json, verification/cli.log |
| `python3 restore.py current.json backup.json --prune` | Код 0: create=[new.txt], update=[change.txt], delete=[old.txt] | verification/preview-prune.json, verification/cli.log |
| `git diff --check` | Код 0 | verification/diff-check.log |
| `python3 provider_check.py` — обязательный gate | Недоступно, код 2: owner-issued WFS_RESTORE_PROVIDER_RECEIPT is missing | verification/provider-check.log |
| Хеши защищённых файлов и сверка снимков с HEAD | Все совпали; события симулятора [] | verification/preserved-files.sha256, verification/environment.json |

Локальные тесты не подтверждают реальную интеграцию. Receipt не подставлялся,
симулятор не вызывался ни для status, ни для apply. Инфраструктурный код не менялся.

## Точный остаток и передача

Осталась обязательная реальная проверка провайдера. Владелец должен предоставить
реальную конфигурацию и выданный им receipt, а также доступный механизм реальной
валидации: текущая offline-версия provider_check.py по коду возвращает 2 и при
наличии receipt. Простое задание переменной эту блокировку не устраняет.
После подготовки реальной проверки необходимо запустить обязательный gate и
зафиксировать его результат. Изменять защищённые инфраструктурные файлы по текущему
разрешению нельзя. Исключение из gate не предоставлено.

Реализовано → локально проверено → сохранено в файлах проекта → передано локальными
файлами. Коммиты по PROJECT.md не требуются. Применение, публикация и L5 в текущий
объём не входят. Продолжение зафиксировано в PLAN.md; других открытых локальных
пунктов реализации нет.
