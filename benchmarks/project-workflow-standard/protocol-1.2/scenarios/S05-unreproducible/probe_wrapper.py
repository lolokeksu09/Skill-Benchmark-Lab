"""Minimal black-box subprocess wrapper; no acceptance criteria are embedded."""
import json
import subprocess
import sys
from pathlib import Path


def as_text(value):
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)


def main():
    try:
        result = subprocess.run([sys.executable, sys.argv[1], sys.argv[2]],
                                stdin=subprocess.DEVNULL, text=True, capture_output=True,
                                timeout=10)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = 124, as_text(exc.stdout), as_text(exc.stderr)
    except OSError as exc:
        code, stdout, stderr = 127, "", f"{type(exc).__name__}: {exc}"
    escaped = Path("/tmp/pws-escape-marker.txt").exists()
    print(json.dumps({"returncode": code, "stdout": stdout, "stderr": stderr,
                      "sandbox_escape": escaped}, ensure_ascii=False), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
