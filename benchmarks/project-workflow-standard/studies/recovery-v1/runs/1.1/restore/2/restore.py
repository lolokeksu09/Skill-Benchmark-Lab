"""Preview the changes needed to restore a backup, without applying them."""

import argparse
import json
from pathlib import Path


def build_plan(current, backup, prune=False):
    """Return sorted paths to create, update, and optionally delete."""
    return {
        "create": sorted(backup.keys() - current.keys()),
        "update": sorted(
            path for path in backup
            if path in current and backup[path] != current[path]
        ),
        "delete": sorted(current.keys() - backup.keys()) if prune else [],
    }


def load_snapshot(path):
    """Read a JSON object mapping paths to string contents."""
    try:
        with path.open(encoding="utf-8") as source:
            snapshot = json.load(source)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{path}: invalid JSON ({error.msg}, "
            f"line {error.lineno}, column {error.colno})"
        ) from error
    except UnicodeError as error:
        raise ValueError(f"{path}: input must be valid UTF-8") from error

    if not isinstance(snapshot, dict):
        raise ValueError(f"{path}: expected a JSON object mapping paths to strings")
    for name, content in snapshot.items():
        if not isinstance(content, str):
            raise ValueError(f"{path}: content for {name!r} must be a string")
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", type=Path, help="current files as a JSON object")
    parser.add_argument("backup", type=Path, help="backup files as a JSON object")
    parser.add_argument(
        "--prune", action="store_true",
        help="include paths absent from the backup in the deletion preview",
    )
    args = parser.parse_args(argv)
    try:
        current = load_snapshot(args.current)
        backup = load_snapshot(args.backup)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(build_plan(current, backup, args.prune), ensure_ascii=False))


if __name__ == "__main__":
    main()
