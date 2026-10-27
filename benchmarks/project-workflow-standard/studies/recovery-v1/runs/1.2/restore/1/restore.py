"""Build a preview of file changes without applying a restore."""

import argparse
import json
import sys


def build_plan(current, backup, prune=False):
    """Compare path-to-string snapshots and return sorted proposed changes."""
    return {
        "create": sorted(path for path in backup if path not in current),
        "update": sorted(
            path for path, content in backup.items()
            if path in current and current[path] != content
        ),
        "delete": sorted(path for path in current if path not in backup) if prune else [],
    }


def load_snapshot(path):
    """Read a UTF-8 JSON object whose values are file-content strings."""
    try:
        with open(path, encoding="utf-8") as source:
            snapshot = json.load(source)
    except OSError as exc:
        raise ValueError(f"{path}: cannot read JSON file: {exc.strerror}") from exc
    except UnicodeError as exc:
        raise ValueError(f"{path}: cannot read UTF-8 JSON") from exc
    except ValueError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc

    if not isinstance(snapshot, dict):
        raise ValueError(f"{path}: expected a JSON object mapping paths to strings")
    for file_path, content in snapshot.items():
        if not isinstance(content, str):
            raise ValueError(f"{path}: content for {file_path!r} must be a string")
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", help="current snapshot as a UTF-8 JSON object")
    parser.add_argument("backup", help="backup snapshot as a UTF-8 JSON object")
    parser.add_argument("--prune", action="store_true", help="include proposed deletions")
    args = parser.parse_args(argv)
    try:
        current = load_snapshot(args.current)
        backup = load_snapshot(args.backup)
    except ValueError as exc:
        parser.error(str(exc))

    json.dump(build_plan(current, backup, prune=args.prune), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
