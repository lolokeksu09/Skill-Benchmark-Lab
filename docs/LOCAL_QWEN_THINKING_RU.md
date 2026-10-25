# Режим Thinking: новое двухплечевое испытание Qwen3-8B

Запускаются те же файлы и критерии Web-сценария, но с директивой `/think` вместо `/no_think`.

- `control` — без Skills.
- `development` — оригинальные инструкции двух навыков из SHA-256-проверенного ZIP DDS 2.0.5.

В обоих режимах одинаковая температура `0.2`, `max_tokens=768`, контекст текущего сервера 2048 и одна модель. Для DDS входной запрос длиннее, что влияет на длительность. Новая серия не подменяет четыре старых измерения. Необходимы отдельные повторные прогоны для устойчивых выводов.

## Один шаг в Termux (сначала контроль)

```bash
cd "$HOME/Skill-Benchmark-Lab" && git pull --ff-only && python -m evaluator.thinking_pilot --variant control
```

Затем (после просмотра результата) второй режим:

```bash
python -m evaluator.thinking_pilot --variant development
```

Сохраняется JSONL `results/raw/local-qwen-web-thinking-{control,development}.jsonl`, сырой ответ API вместе с reasoning и итоговый кандидат отдельно под `results/raw/local-qwen-web-candidates/thinking/`. Сгенерированный JavaScript **не исполняется**. Если генерация обрезана по `finish_reason=length`, это неуспешный кандидат. Отсутствие `reasoning_present` не доказывает, что сервер не использовал Thinking: конкретная версия API может не отдавать его явно.

Если превышен лимит контекста, ошибка фиксируется — нельзя менять лимит лишь для одного режима и считать их сравнимыми.
