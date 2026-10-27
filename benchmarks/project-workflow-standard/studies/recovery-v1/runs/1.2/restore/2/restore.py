"""Compute a restore preview without writing snapshot or destination files."""

import argparse
import json


def build_plan(current, backup, prune=False):
    """Return sorted paths to create, update, and optionally delete."""
    return {
        "create": sorted(path for path in backup if path not in current),
        "update": sorted(
            path for path in backup if path in current and current[path] != backup[path]
        ),
        "delete": sorted(path for path in current if path not in backup) if prune else [],
    }


def load_snapshot(path):
    """Read a UTF-8 JSON object mapping paths to string contents."""
    try:
        with open(path, encoding="utf-8") as source:
            snapshot = json.load(source)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{path}: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    except UnicodeError as error:
        raise ValueError(f"{path}: input must use UTF-8 encoding") from error

    if not isinstance(snapshot, dict):
        raise ValueError(f"{path}: expected a JSON object mapping paths to strings")
    for name, contents in snapshot.items():
        if not isinstance(contents, str):
            raise ValueError(f"{path}: content for path {name!r} must be a string")
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", help="current snapshot JSON file")
    parser.add_argument("backup", help="backup snapshot JSON file")
    parser.add_argument(
        "--prune", action="store_true", help="include obsolete paths in the delete preview"
    )
    args = parser.parse_args(argv)
    try:
        current = load_snapshot(args.current)
        backup = load_snapshot(args.backup)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(build_plan(current, backup, args.prune)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
