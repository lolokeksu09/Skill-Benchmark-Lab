"""Загрузка конфигурации приложения."""

class ConfigError(Exception):
    """Понятная ошибка некорректной конфигурации."""


def parse_timeout(payload):
    """Вернуть положительный timeout из ответа конфигурации."""
    value = int(payload["timeout"])
    if value <= 0:
        raise ConfigError("timeout must be positive")
    return value
