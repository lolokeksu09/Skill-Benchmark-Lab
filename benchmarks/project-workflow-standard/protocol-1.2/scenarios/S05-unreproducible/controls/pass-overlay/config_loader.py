class ConfigError(Exception):
    pass


def parse_timeout(payload):
    try:
        value = int(payload["timeout"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError("timeout must be a positive integer") from exc
    if value <= 0:
        raise ConfigError("timeout must be positive")
    return value
