import json
import sys
from config_loader import ConfigError, parse_timeout


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python cli.py CONFIG.json")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            timeout = parse_timeout(json.load(fh))
    except (OSError, json.JSONDecodeError, ConfigError) as exc:
        print(f"configuration error: {exc}")
        return 1
    print(f"timeout={timeout}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
