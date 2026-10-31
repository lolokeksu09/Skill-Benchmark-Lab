# Project Workflow Benchmark — Protocol 1.2 Pilot

Версионированный стенд для парного сравнения Project Workflow Standard v1.3 и v1.4-rc3. Старые результаты `../runs`, `../results` и протокол v1.1/v1.2 не изменяются и не смешиваются с этим стендом.

## Статус

Агентных запусков: **0 из 4**. Преимущество любой версии не установлено. Реализованы только S05 и S06. CI проверяет runner и детерминированные controls; CI не вызывает AI и не выполняет публикацию. Auditable AI runner bridge (`tools/agent_runner.py`) реализован и проверяется в CI детерминированными fake-agent controls без AI-провайдера и без credentials.

## Модель изоляции

- Candidate-код выполняется только в новом Docker-контейнере: `--network none`, read-only root и read-only `/work` во время оценки, `cap-drop=ALL`, `no-new-privileges`, непривилегированный UID.
- cgroup ограничивает память, PID и CPU всего дерева контейнера; host fallback и host-режим controls отсутствуют.
- Evaluator, controls, другие запуски и метаданные находятся вне `/work`. Candidate не получает Docker socket, токены или сетевые учётные данные.
- Все candidate-файлы читаются через `tools/safe_io.py`: symlink, FIFO и другие специальные файлы отклоняются; размер ограничен.
- Тег образа используется только для preflight pull. Выполнение и аттестация привязаны к разрешённому `sha256` digest.

Docker делит ядро с host и не эквивалентен VM. Это пилотная граница для недоверенного candidate-кода при доверенном Docker daemon; для более сильной угрозы нужна отдельная VM.

## AI runner bridge

`tools/agent_runner.py` — реализованный fail-closed мост между trusted orchestrator и внешней AI-командой. Внешняя команда не получает путь workspace и не наследует host environment (только `PATH`/`HOME` и явные `--allow-env`). Весь доступ к workspace идёт через JSON-lines протокол `pws-agent-bridge-v1` с инструментами `list_files`, `read_file`, `write_file`, `run_tests`, `finish`; каждое сообщение попадает в `tool-log.jsonl` (значения длиннее 4096 символов логируются как sha256+preview с флагом `truncated`, у лога есть байтовый бюджет). `run_tests` для S05 выполняет candidate-тесты только в Docker-контейнере с preflight image и не может превысить общий deadline прогона; для S06 недоступен. `TASK.md` и `_standard/` являются immutable входами: `write_file` отклоняет их без остановки прогона. Неизвестные инструменты, malformed-сообщения и path traversal закрывают прогон; общий deadline enforced watchdog-терминацией всей process group — killpg выполняется безусловно, чтобы не оставить сирот в группе процессов агента (дочерний процесс, создавший собственную сессию, требует изоляции уровня ОС, см. trusted adapter ниже). Мост пишет **неподписанный** evidence payload; подпись runner key (`pws-runner-v1`) выполняется оператором отдельно. CI проверяет мост только детерминированными fake-агентами: позитивные bindings, forbidden tool, traversal, timeout, изоляцию environment, недоступность `run_tests` в S06, убийство сирот, malformed-схему, non-zero exit после finish, immutable inputs, бюджет лога, раскрытие `--allow-env`. Реальный AI не вызывается.

### Trusted adapter и границы evidence

Внешняя AI-команда является доверенной частью runner (trusted adapter): до пилота оператор обязан зафиксировать её идентичность (имя, версия, источник или digest) в записях прогона вне workspace. `--allow-env` допускает только оператор-одобренные переменные; они раскрываются в evidence (`trusted_side.allow_env`) и не должны включать AI-провайдер credentials. Если адаптер нельзя считать доверенным, он должен выполняться под изоляцией уровня ОС (отдельный пользователь, контейнер или VM) — это вне охвата данного протокола. SSH-подпись доказывает происхождение evidence (ключ под контролем подписанта), а не истинность утверждений: `accepted=true` означает прохождение fail-closed механических проверок для подписанных артефактов, а не истинность claims.

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

## Слепое рецензирование и непрозрачные идентификаторы

`run_id` содержит только ID сценария и случайный hex; он не кодирует версию или repeat и **не доказывает назначенную версию**. `RUN.json` с `standard_tree_sha256` остаётся приватным для доверенного runner и не передаётся рецензенту. Версия выводится при сравнении пар исключительно из trusted `_standard/` tree. Приватное соответствие `run_id → standard` хранится отдельно от публичного `pilot-manifest.json` и reviewer-visible evidence. Само значение `standard_tree_sha256` раскрывает версию при сопоставлении с публичным manifest, поэтому его нельзя включать в blinded review packet.
