# Передача результата архивного аудита

- PR: [Skill-Benchmark-Lab #46](https://github.com/lolokeksu09/Skill-Benchmark-Lab/pull/46), ветка `audit/pws-v1.4-archive`; merge и релиз не выполнялись.
- Первая GitHub-ревизия проверенного дерева: [398a5daf5eb26f2c4104f6b68d769093d2d17e90](https://github.com/lolokeksu09/Skill-Benchmark-Lab/commit/398a5daf5eb26f2c4104f6b68d769093d2d17e90). Дерево `7b967d9e0798b79f4217a00745ab5eee41baf7c6` совпало с локальным `92ea3d0`.
- [Первый архивный CI](https://github.com/lolokeksu09/Skill-Benchmark-Lab/actions/runs/41344753507) — success; [старый replay](https://github.com/lolokeksu09/Skill-Benchmark-Lab/actions/runs/41344753460) — success.
- В первом PR CI checkout был стандартным merge ref `084cd1316fb0354bcc0acc15a90abfc071c66ec0`, а не head. Провереное содержимое ZIP идентично локальному. Для финальной приёмки workflow изменён на explicit head checkout и проверяет `--expected-revision`; финальный head/run/состояние записываются в CI-FINAL.json передаваемого пакета и в ответе. Это уточнение CI не меняет 16 файлов кандидата или критерии сравнения.
- CI фактически использовал Python 3.12.3; локальные измерения — Python 3.12.14.

## Артефакты

| Файл | Подтверждение |
|---|---|
| Project-Workflow-Standard-v1.4-rc4.zip | 16 исходных имён файлов; CRC и равенство дереву проверены локально и CI; SHA-256 `60cd83df4c494d83153436fb1ff5e194d1378d8b33e9c9b30cd99a207e88e999` |
| Project-Workflow-Standard-v1.4-Archive-Audit.zip | Отчёты, rc3/v1.3/rc4, протокол, тесты, исходные результаты и логи; отдельная контрольная сумма в SHA256SUMS.txt |
| pws-archive-history.bundle | Полная локальная Git-история до `92ea3d0`, включая предрегистрационный `2860f24`; `git bundle verify` успешен |

Native git push не имел учётных данных; GitHub-публикация выполнена подключённым API с проверкой blob SHA и итогового tree SHA. Поэтому локальные SHA `2860f24`/`92ea3d0` не выдаются за удалённые GitHub-коммиты. Локальная предрегистрация не имеет независимой внешней временной аттестации.

Статус результата: **архив проверен, кандидат rc4 подготовлен, PR открыт**. Final и доказанное улучшение работы ИИ не заявлены. Метрики приложений, токены/стоимость, реальные разрешения по одному JSON и переносимость защищённого скрипта на Windows не подтверждены. Дополнительных разрешений на production эта передача не создаёт.
