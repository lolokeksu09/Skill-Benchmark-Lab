# Structural validation

Этот файл не содержит агентных результатов. Авторитетный статус runner определяется только выводом `tools/preflight.py` и точным CI job. Перед сохранением изменений выполняется `tools/validate.py --static-only`; полный режим дополнительно требует `READY` preflight и запускает все Docker controls. Результаты CI добавляются в PR, а не задним числом в замороженные fixtures.
