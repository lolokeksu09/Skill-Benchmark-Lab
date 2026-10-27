"""Build a validated version 2 package manifest."""

import argparse
import json
import os
from pathlib import Path
import tempfile


def build_manifest(records):
    """Normalize records, rejecting invalid names, sizes and duplicates."""
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    items = []
    names = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        name = record.get("name")
        if not isinstance(name, str):
            raise ValueError(f"record {index}: name must be a string")
        name = name.strip()
        if not name:
            raise ValueError(f"record {index}: name must not be empty")
        normalized_name = name.casefold()
        if normalized_name in names:
            raise ValueError(f"record {index}: duplicate name {name!r}")

        size = record.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool):
            raise ValueError(f"record {index}: bytes must be an integer")
        if size < 0:
            raise ValueError(f"record {index}: bytes must be non-negative")
        names.add(normalized_name)
        items.append({"name": name, "bytes": size})

    items.sort(key=lambda item: item["name"].casefold())
    return {
        "version": 2,
        "items": items,
        "total_bytes": sum(item["bytes"] for item in items),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON list of name/bytes records")
    parser.add_argument("--output", required=True, help="destination manifest JSON")
    args = parser.parse_args()

    temporary_path = None
    try:
        with open(args.input, encoding="utf-8") as source:
            try:
                records = json.load(source)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON: {error}") from error
        manifest = build_manifest(records)
        output = Path(args.output)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            json.dump(manifest, destination, ensure_ascii=False, indent=2)
            destination.write("\n")
        os.replace(temporary_path, output)
        temporary_path = None
    except (OSError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
