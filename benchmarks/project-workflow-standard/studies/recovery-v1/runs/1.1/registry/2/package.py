import argparse
import json
import os
from pathlib import Path
import tempfile


def build_manifest(records):
    """Validate records and return a normalized version 2 manifest."""
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    items = []
    names = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"record {index}: name must be a nonempty string")
        name = name.strip()
        key = name.casefold()
        if key in names:
            raise ValueError(f"record {index}: duplicate name {name!r}")
        size = record.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError(f"record {index}: bytes must be a nonnegative integer")
        names.add(key)
        items.append({"name": name, "bytes": size})

    items.sort(key=lambda item: item["name"].casefold())
    return {"version": 2, "items": items,
            "total_bytes": sum(item["bytes"] for item in items)}


def main():
    parser = argparse.ArgumentParser(description="Build a version 2 manifest.")
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    temporary_path = None
    try:
        with open(args.input, encoding="utf-8") as source:
            manifest = build_manifest(json.load(source))
        output = Path(args.output)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            json.dump(manifest, destination, indent=2)
            destination.write("\n")
        os.replace(temporary_path, output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
