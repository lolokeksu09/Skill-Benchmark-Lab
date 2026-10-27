"""Build a version 2 package manifest from a JSON list of file records."""

import argparse
import json
import os
from pathlib import Path
import tempfile


def build_manifest(records):
    """Normalize records and return a manifest, or raise ValueError."""
    if not isinstance(records, list):
        raise ValueError("input must be a list of records")

    items = []
    seen = set()
    total_bytes = 0
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"record {index}: expected an object")
        name = record.get("name")
        if not isinstance(name, str):
            raise ValueError(f"record {index}: name must be a string")
        name = name.strip()
        if not name:
            raise ValueError(f"record {index}: name must not be empty")
        key = name.casefold()
        if key in seen:
            raise ValueError(f"record {index}: duplicate name {name!r}")

        size = record.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int):
            raise ValueError(f"record {index}: bytes must be an integer (not bool)")
        if size < 0:
            raise ValueError(f"record {index}: bytes must be non-negative")

        seen.add(key)
        items.append({"name": name, "bytes": size})
        total_bytes += size

    items.sort(key=lambda item: item["name"].casefold())
    return {"version": 2, "items": items, "total_bytes": total_bytes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON list of file records")
    parser.add_argument("--output", required=True, help="destination manifest JSON")
    args = parser.parse_args()

    temporary_path = None
    try:
        with open(args.input, encoding="utf-8") as source:
            manifest = build_manifest(json.load(source))
        output_path = Path(args.output)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output_path.parent,
            prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
        ) as output:
            temporary_path = Path(output.name)
            json.dump(manifest, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(temporary_path, output_path)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
