# Termux: локальный Qwen3-8B — первый Web-пилот

Этот шаг запускает **только контрольный режим (без Skills)**. Это не сравнение пяти вариантов и не доказательство качества исправленного кода.

## Требования

- Запущенный на телефоне `llama-server`, модель Qwen3-8B, API `127.0.0.1:8080`.
- Обычный Termux с `python` (Debian/PRoot не требуется).
- Ветка лаборатории `bench/local-qwen-termux-pilot`.

## Команды во втором сеансе Termux

```sh
pkg install -y python git
git clone --branch bench/local-qwen-termux-pilot https://github.com/lolokeksu09/Skill-Benchmark-Lab.git
cd Skill-Benchmark-Lab
python -m unittest discover -s tests -v
python -m evaluator.local_llama --repeats 1 --max-tokens 400
```

Результат будет в `results/raw/local-qwen-web-pilot.jsonl`; сырой ответ — в `results/raw/local-qwen-web-candidates/trial-001.txt`. Папка уже исключена из Git.

Каждая попытка отправляет независимый запрос без истории. В ответах сохраняются число токенов и время, фактически полученные от llama-server. Отсутствующие поля не выдумываются. Ошибочные ответы тоже фиксируются. Если файл отчёта уже существует, инструмент не перезапишет его.

**Важно:** ни один сгенерированный файл не исполняется на смартфоне автоматически. Перед выполнением JavaScript его следует просмотреть и тестировать изолированно. Следующий этап — настоящая загрузка замороженных ZIPов P2P и Development Skills и запуск пяти режимов с доступным контекстом, после отдельного пилота.


## Проверка кандидата без выполнения JavaScript

После контрольного прогона можно проверить уже сохранённый ответ модели. В каталоге репозитория:

```bash
git pull --ff-only
python -m evaluator.candidate_checks --candidate results/raw/local-qwen-web-candidates/trial-001.txt
```

Этот анализ специально ограничен двумя файлами Web-стенда. Программа **не запускает** JavaScript. Для первого известного ответа Qwen с `encodeURIComponent(post.title)`, отсутствующим `aria-label` и `max-width: 100%` выдаст: 1 статическое совпадение, 2 обнаруженные ошибки.

В будущих прогонах `evaluator.local_llama` автоматически записывает объект `static_preflight` в строку JSONL вместе с реальными токенами и временем. **Нельзя считать `static_preflight` результатом Node-тестов:** распознавание верного HTML-экранирования без исполнения кода даёт статус `possible`, а неизвестные реализации — `unknown`. Полная проверка требует отдельного безопасного окружения для запуска полученного кода.
