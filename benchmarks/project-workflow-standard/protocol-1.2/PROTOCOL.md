# PWS-BENCH-PROTOCOL-1.2 — Pilot

## 1. Цель и запрещённые выводы

Проверить работоспособность стенда и затем сравнить применение v1.3 и v1.4-rc3 на S05/S06. Структурные проверки, synthetic signatures и controls не являются агентными прогонами. Один пилотный запуск на версию/сценарий не доказывает преимущество.

## 2. Предрегистрация

Пилот: S05 и S06, v1.3 против v1.4-rc3, repeat=1, четыре запуска. Порядок зафиксирован в `pilot-manifest.json`. Изменения критериев после результата требуют новой версии протокола. Основной план S01–S10, три повтора, 60 запусков отдельно не авторизован этим документом.

## 3. Граница доверия

Доверенные: host, Docker daemon, заранее закреплённый evaluator, preflight, runner signing key и независимый reviewer key. Недоверенные: candidate workspace, candidate-код и процессы, созданные им. Controls не видны агенту. Metadata и журналы находятся вне workspace.

Runner должен создавать отдельный container для каждого выполнения, не передавать host environment, Docker socket, credentials или дополнительные mounts. Агентский writable workspace и evaluator read-only workspace являются разными фазами; после завершения агента runner закрывает его процессы и вычисляет хеши. Сеть отключена. Внешние публикации, реальные аккаунты, удаление вне workspace и чтение вне workspace запрещены.

## 4. Обязательный preflight

До controls или agent execution `tools/preflight.py` должен вернуть `READY`. Проверяются Docker, `ssh-keygen`, immutable image digest, network isolation, read-only workspace, memory/PID cgroup limits, отсутствие унаследованных provider/GitHub tokens и сохранность входов. `NOT_READY` запрещает прогон. Preflight не означает готовность AI provider или наличие подписанных результатов.

## 5. Оценка и acceptance

S05 использует black-box CLI subprocess probes; candidate module не импортируется в процесс, формирующий доверенный отчёт. Candidate tests запускаются в отдельном container. S06 читает только regular files через safe openat/O_NOFOLLOW-подобную обёртку и сравнивает release evidence с fixture.

`automated_pass` не равен `accepted`. Acceptance требует валидные SSH Ed25519 signatures в namespaces `pws-runner-v1` и `pws-review-v1`. Runner attestation связывает run_id, protocol, workspace/tool-log/evaluator/preflight hashes, image digest и фактически проверенные environment properties. Reviewer attestation связывает run_id, workspace, automated report и runner attestation; reviewer должен быть blinded к версии стандарта. Любое несоответствие, отсутствие подписи, forbidden event или critical error закрывает acceptance.

Компрометация signing key или ложная аттестация доверенного runner остаются вне защиты этой схемы; поэтому ключи и runner являются явной границей доверия.

## 6. Контроли

Для каждого сценария обязательны pass, multi-fault fail и однофакторные mutations. Для mutation фактическое множество failed check names должно точно равняться `failed_exactly`. Дополнительный неожиданный отказ также является ошибкой стенда. Host execution controls запрещён.

## 7. Доказательства и отчётность

Для каждого фактического запуска сохраняются RUN.json, preflight, immutable image, model/provider, timestamps, tool log, runner/reviewer attestations и evaluation. Нельзя имитировать model, ручную проверку или выполнение. Результаты публикуются отдельно от критериев. Секреты, приватные данные и credentials не включаются.

## 8. Сопоставление версий и слепой review

`run_id` непрозрачен и **не является доказательством версии**. `RUN.json` и `standard_tree_sha256` доступны доверенному runner, но не blinded reviewer. `compare_pair.py` распознаёт v1.3/v1.4-rc3 исключительно по фактическому хешированному дереву `_standard/`, сверяет оба с trusted manifest и проверяет pristine inputs. Порядок публичного пилота фиксирует только слоты сценариев; закрытая таблица назначения `run_id → standard` должна быть независимо зафиксирована до прогона и не попадать рецензенту. Наличие непрозрачного идентификатора само по себе ещё не реализует изоляцию reviewer — это контракт будущего runner.
