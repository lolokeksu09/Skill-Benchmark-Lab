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
            raise ValueError(f"record {index}: expected an object with name and bytes")
        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"record {index}: name must be a nonempty string")
        name = name.strip()
        key = name.casefold()
        if key in names:
            raise ValueError(f"record {index}: duplicate name {name!r}")
        size = record.get("bytes")
        if type(size) is not int or size < 0:
            raise ValueError(f"record {index}: bytes must be a nonnegative integer (not bool)")
        names.add(key)
        items.append({"name": name, "bytes": size})

    items.sort(key=lambda item: item["name"].casefold())
    return {
        "version": 2,
        "items": items,
        "total_bytes": sum(item["bytes"] for item in items),
    }


def main():
    parser = argparse.ArgumentParser(description="Build a version 2 package manifest.")
    parser.add_argument("input", help="JSON array of records with name and bytes")
    parser.add_argument("--output", required=True, help="destination JSON manifest")
    args = parser.parse_args()

    temporary_path = None
    try:
        with open(args.input, encoding="utf-8") as source:
            try:
                records = json.load(source)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON: {error}") from error
        manifest = build_manifest(records)
        output_path = Path(args.output)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output_path.parent,
            prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
        ) as output:
            temporary_path = Path(output.name)
            json.dump(manifest, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(temporary_path, output_path)
        temporary_path = None
    except (OSError, ValueError) as error:
        parser.error(str(error))
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
