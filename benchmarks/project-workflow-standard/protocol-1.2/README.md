# Project Workflow Benchmark — Protocol 1.2 Pilot

Версионированный стенд для парного сравнения Project Workflow Standard v1.3 и v1.4-rc3. Старые результаты `../runs`, `../results` и протокол v1.1/v1.2 не изменяются и не смешиваются с этим стендом.

## Статус

Агентных запусков: **0 из 4**. Преимущество любой версии не установлено. Реализованы только S05 и S06. CI проверяет runner и детерминированные controls; CI не вызывает AI и не выполняет публикацию.

## Модель изоляции

- Candidate-код выполняется только в новом Docker-контейнере: `--network none`, read-only root и read-only `/work` во время оценки, `cap-drop=ALL`, `no-new-privileges`, непривилегированный UID.
- cgroup ограничивает память, PID и CPU всего дерева контейнера; host fallback и host-режим controls отсутствуют.
- Evaluator, controls, другие запуски и метаданные находятся вне `/work`. Candidate не получает Docker socket, токены или сетевые учётные данные.
- Все candidate-файлы читаются через `tools/safe_io.py`: symlink, FIFO и другие специальные файлы отклоняются; размер ограничен.
- Тег образа используется только для preflight pull. Выполнение и аттестация привязаны к разрешённому `sha256` digest.

Docker делит ядро с host и не эквивалентен VM. Это пилотная граница для недоверенного candidate-кода при доверенном Docker daemon; для более сильной угрозы нужна отдельная VM.

## Проверка

```bash
python3 tools/validate.py --static-only
python3 tools/preflight.py --output /tmp/pws-preflight.json
python3 tools/validate.py --preflight /tmp/pws-preflight.json
```

`preflight` завершается ненулевым кодом при `NOT_READY`. Нельзя заменять Docker запуском candidate-кода на host. Static-only режим не проверяет изоляцию и не является полным прохождением.

## Подписанные доказательства

JSON-поля `status=executed`, `verified_by_runner` или `approved=true` не являются доказательством. Для `accepted=true` требуются:

1. matching `READY` preflight;
2. runner attestation с SSH Ed25519-подписью, привязанная к run_id, workspace, tool log, evaluator и preflight;
3. чистый attested tool log;
4. отдельная подпись blinded reviewer, привязанная к automated report и runner attestation.

Доверенные публичные ключи задаются отдельным `allowed_signers`; закрытые ключи хранятся вне workspace и репозитория. Секреты не передаются в чат. Пример — `attestations/allowed_signers.example`.

## Пилот

`prepare_run.py` создаёт bundle, но не запускает агента. `compare_pair.py` требует одинаковый сценарий/repeat, одинаковые non-standard входы и две разные trusted standard trees. Mutation expectations являются точными множествами failed checks, а не subset.

До независимого review исправлений и успешного Docker preflight четыре агентных пилота не запускаются. Основной benchmark на 60 запусков не начат.
