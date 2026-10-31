#!/usr/bin/env python3
"""Optional, dependency-free structural checks for Project Workflow Standard 1.4-rc3.

Usage: python tools/check_standard.py .
       python tools/check_standard.py /path/to/Project-Workflow-Standard-v1.4-rc3.zip

These checks are syntactic invariants only: they do not execute or assess agents.
"""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

VERSION = "1.4-rc3"
ORIGINAL = {
    "AGENTS.md", "PROJECT.md", "README.md", "TESTING-LEVELS.md",
    "templates/AUDIT.md", "templates/CONTINUATION.md", "templates/PLAN.md",
    "templates/RELEASE.md", "templates/VERIFICATION.md",
}
EXTRA = {
    "CHANGELOG.md", "VALIDATION.md", "examples/README.md",
    "examples/01-light-documentation.md", "examples/02-bug-traceability.md",
    "examples/03-release-boundary.md", "tools/check_standard.py",
}
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def load(path: Path) -> tuple[dict[str, bytes], str]:
    if path.is_file():
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise ValueError("ZIP CRC failed")
            names = [i.filename for i in z.infolist() if not i.is_dir()]
            if len(names) != len(set(names)):
                raise ValueError("duplicate ZIP entry")
            for name in names:
                p = PurePosixPath(name)
                if p.is_absolute() or ".." in p.parts or not p.parts:
                    raise ValueError(f"unsafe ZIP path: {name}")
            return {name: z.read(name) for name in names}, "ZIP (CRC passed)"
    if path.is_dir():
        return {p.relative_to(path).as_posix(): p.read_bytes()
                for p in path.rglob("*") if p.is_file()}, "directory (ZIP CRC not applicable)"
    raise FileNotFoundError(path)


def check(src: Path) -> int:
    try:
        files, archive_result = load(src)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(f"FAIL loading input: {e}", file=sys.stderr)
        return 1

    failed = 0
    def test(name: str, fn):
        nonlocal failed
        try:
            note = fn()
            print(f"PASS {name}" + (f": {note}" if note else ""))
        except (AssertionError, UnicodeError, ValueError, KeyError) as e:
            failed += 1
            print(f"FAIL {name}: {e}")

    texts = {}
    def structure(original_only=False):
        wanted = ORIGINAL if original_only else ORIGINAL | EXTRA
        missing = sorted(wanted - set(files))
        assert not missing, f"missing: {missing}"
        return f"{len(wanted)} expected files present"

    def markdown():
        docs = [name for name in files if name.endswith(".md")]
        assert len(docs) == 15, f"expected 15 Markdown files, got {len(docs)}"
        return f"{len(docs)} Markdown documents"

    def utf8():
        for name, raw in files.items():
            if name.endswith(".md") or name.endswith(".py"):
                texts[name] = raw.decode("utf-8-sig")
        return f"{len(texts)} readable sources"

    def links():
        found = 0
        for name, content in texts.items():
            if not name.endswith(".md"):
                continue
            origin = PurePosixPath(name).parent
            for line_no, line in enumerate(content.splitlines(), 1):
                for m in LINK.finditer(line):
                    ref = m.group(1).split("#", 1)[0].strip()
                    if not ref or re.match(r"^[a-z][a-z0-9+.-]*:", ref, re.I):
                        continue
                    target = origin / ref
                    parts = []
                    for part in target.parts:
                        if part == "..":
                            if not parts: raise AssertionError(f"link above archive root: {name}:{line_no} {ref}")
                            parts.pop()
                        elif part not in ("", "."):
                            parts.append(part)
                    resolved = "/".join(parts)
                    assert resolved in files or any(k.startswith(resolved.rstrip("/") + "/") for k in files), f"missing {name}:{line_no} -> {ref}"
                    found += 1
        assert found > 0, "no local links detected"
        return f"{found} local links resolve"

    def versions():
        locations = ["README.md", "TESTING-LEVELS.md", "CHANGELOG.md", "VALIDATION.md"]
        for name in locations:
            assert VERSION in texts[name], f"{name} does not mention {VERSION}"
        assert texts["README.md"].splitlines()[0].endswith(VERSION), "README title mismatch"
        assert f"## {VERSION} " in texts["CHANGELOG.md"], "CHANGELOG current entry missing"

    def norms():
        a = texts["AGENTS.md"]
        t = texts["TESTING-LEVELS.md"]
        assert "режимы **документирования**" in a
        assert "не строгость проверок" in t
        assert "воспроизведён либо ограничение воспроизведения" in t
        assert "не** доказывает устранение исторической причины" in t
        assert "**«без исключений»**" in t and "**«с исключениями: EXC-ID…»**" in t
        assert "Gate с применимым активным исключением" in t
        assert "а не «успех»" in t
        assert "не переносится автоматически" in t
        assert "поставку" in t
        return "selected textual safeguards present (not semantic proof)"

    def templates():
        plan = texts["templates/PLAN.md"]
        ver = texts["templates/VERIFICATION.md"]
        ex2 = texts["examples/02-bug-traceability.md"]
        rel = texts["templates/RELEASE.md"]
        method = texts["VALIDATION.md"]
        assert "REQ-ID" in plan and "REQ-ID" in ver
        assert "либо** подтверждённые факты" in ver
        assert "**Mock подтверждает только моделируемую область**" in ex2
        assert "с исключениями" in rel
        assert "количество повторов" in method
        assert "новой версией протокола" in method
        assert "не подтверждённое улучшение" in texts["README.md"]
        return "key examples and templates aligned (textual only)"

    print(f"Source: {src}")
    test("1. Input and archive integrity", lambda: archive_result)
    test("2. Preserve original documents", lambda: structure(original_only=True))
    test("3. Complete package structure", lambda: (structure(), markdown())[1])
    test("4. UTF-8 decoding", utf8)
    if len(texts) == 0:
        print("FAIL dependent checks: UTF-8 decoding not completed")
        return 1
    test("5. Local links", links)
    test("6. Version consistency", versions)
    test("7. Core rule markers", norms)
    test("8. Template and protocol markers", templates)
    print(f"Result: {8-failed}/8 checks passed; no agent behavior evaluated")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args()
    sys.exit(check(args.path))
