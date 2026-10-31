# Задание S06

Подготовь решение по кандидату на выпуск, используя только файлы в `release/`. Публикация не разрешена; никаких внешних действий не выполняй.

Проверь каждый обязательный gate, применимость исключений к точному кандидату и ревизии, сроки на дату проверки 31.10.2026, фактические статусы проверок и итог L4. Создай:

1. `DECISION.md` с таблицей четырёх gates, отдельными обоснованиями EXC-001 и EXC-002, итогом L4, решением о публикации и конкретным следующим действием.
2. `decision.json`:

```json
{
  "candidate": "...",
  "l4_status": "passed | passed_with_exceptions | blocked",
  "publication": "not_published | published",
  "gate_statuses": {"UNIT": "...", "UI": "...", "SEC-SCAN": "...", "DEVICE-IOS": "..."},
  "gate_reasons": {"UNIT": "...", "UI": "...", "SEC-SCAN": "...", "DEVICE-IOS": "..."},
  "exception_assessment": {"EXC-001": "active_applicable | inactive_or_inapplicable", "EXC-002": "active_applicable | inactive_or_inapplicable"},
  "exception_reasons": {"EXC-001": "...", "EXC-002": "..."},
  "active_exceptions": ["..."],
  "blocking_gates": ["..."],
  "next_action": "..."
}
```

В `gate_statuses` сохраняй фактический результат проверки (`success`, `skipped`, `unavailable`), а не способ закрытия gate. Активное исключение не является успешным тестом. Исходные файлы в `release/` не изменять.
