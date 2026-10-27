"""Preview snapshot differences without applying any changes."""

import argparse
import json
from pathlib import Path


def _validate_snapshot(snapshot, name):
    if not isinstance(snapshot, dict):
        raise ValueError(f"{name}: expected a JSON object mapping paths to strings")
    for path, content in snapshot.items():
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError(f"{name}: path {path!r} and its content must be strings")


def build_plan(current, backup, prune=False):
    """Return sorted paths to create, update, and optionally delete."""
    _validate_snapshot(current, "current")
    _validate_snapshot(backup, "backup")
    return {
        "create": sorted(path for path in backup if path not in current),
        "update": sorted(
            path for path in backup
            if path in current and current[path] != backup[path]
        ),
        "delete": sorted(path for path in current if path not in backup) if prune else [],
    }


def _load_snapshot(filename):
    try:
        text = Path(filename).read_text(encoding="utf-8")
    except UnicodeError as error:
        raise ValueError(f"{filename}: expected UTF-8 encoded JSON") from error
    except OSError as error:
        raise ValueError(f"{filename}: cannot read file ({error.strerror})") from error
    try:
        snapshot = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{filename}: invalid JSON at line {error.lineno}, column {error.colno}"
        ) from error
    _validate_snapshot(snapshot, filename)
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", help="current snapshot JSON file")
    parser.add_argument("backup", help="backup snapshot JSON file")
    parser.add_argument(
        "--prune", action="store_true", help="include missing paths in the deletion preview"
    )
    args = parser.parse_args(argv)
    try:
        plan = build_plan(
            _load_snapshot(args.current), _load_snapshot(args.backup), args.prune
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
