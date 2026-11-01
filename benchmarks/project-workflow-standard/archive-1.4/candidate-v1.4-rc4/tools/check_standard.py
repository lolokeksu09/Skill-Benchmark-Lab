#!/usr/bin/env python3
"""Dependency-free PWS package and optional evidence-record validator.

This checks bounded files and declared invariants, not agent behavior, log truth,
actual authorization, or the sufficiency of the project's test selection.
Run a reviewed copy of this tool; never execute code from an untrusted ZIP.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit
import zipfile
import zlib

VERSION = "1.4-rc4"
EXPECTED = set("AGENTS.md PROJECT.md README.md TESTING-LEVELS.md CHANGELOG.md VALIDATION.md".split()) | {
    "templates/" + x + ".md" for x in ("AUDIT", "CONTINUATION", "PLAN", "RELEASE", "VERIFICATION")
} | {"examples/README.md", "examples/01-light-documentation.md", "examples/02-bug-traceability.md",
     "examples/03-release-boundary.md", "tools/check_standard.py"}
MAX_FILE = 256 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_ARCHIVE = 4 * 1024 * 1024
MAX_ENTRIES = 64


class Invalid(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Invalid(message)


def canonical(name, directory=False):
    need(isinstance(name, str) and bool(name), "empty/non-string path")
    if directory:
        name = name.removesuffix("/")
    need(not name.startswith("/") and "\\" not in name and ":" not in name and "\x00" not in name,
         "unsafe path: " + repr(name))
    need(all(p not in ("", ".", "..") for p in name.split("/")), "noncanonical path: " + repr(name))
    return name


def read_file(root, name, limit=MAX_FILE):
    """No symlink following at any component; nonregular files never get read."""
    canonical(name)
    need(all(hasattr(os, k) for k in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")) and
         os.open in os.supports_dir_fd, "secure reads require POSIX O_NOFOLLOW and dir_fd")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(root, flags | os.O_DIRECTORY)
    try:
        parts = name.split("/")
        for part in parts[:-1]:
            nxt = os.open(part, flags | os.O_DIRECTORY, dir_fd=fd)
            os.close(fd); fd = nxt
        leaf = os.open(parts[-1], flags, dir_fd=fd)
        with os.fdopen(leaf, "rb") as f:
            info = os.fstat(f.fileno())
            need(stat.S_ISREG(info.st_mode), "not a regular file: " + name)
            need(info.st_size <= limit, "file size limit: " + name)
            data = f.read(limit + 1)
            need(len(data) <= limit, "file read limit: " + name)
            return data
    finally:
        os.close(fd)


def load(src):
    need(not src.is_symlink(), "input is a symlink")
    if src.is_file():
        raw = read_file(src.parent, src.name, MAX_ARCHIVE)
        import io
        result = {}
        total = 0
        seen = set()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            need(len(z.infolist()) <= MAX_ENTRIES, "ZIP entry count limit")
            for info in z.infolist():
                need(info.orig_filename == info.filename, "ZIP filename was truncated/normalized")
                name = canonical(info.filename, info.is_dir())
                need(name not in seen, "duplicate/aliased ZIP path: " + name)
                seen.add(name)
                kind = stat.S_IFMT(info.external_attr >> 16)
                need(kind in (0, stat.S_IFREG, stat.S_IFDIR), "nonregular ZIP entry: " + name)
                need(not (info.flag_bits & 1), "encrypted ZIP entry: " + name)
                if info.is_dir():
                    need(kind in (0, stat.S_IFDIR), "ZIP directory type mismatch")
                    continue
                need(kind in (0, stat.S_IFREG), "ZIP file type mismatch")
                need(info.file_size <= MAX_FILE, "ZIP file size limit: " + name)
                total += info.file_size
                need(total <= MAX_TOTAL, "ZIP total size limit")
                with z.open(info) as f:
                    data = f.read(MAX_FILE + 1)
                need(len(data) == info.file_size and len(data) <= MAX_FILE, "ZIP entry size mismatch")
                result[name] = data  # reading the full bounded entry also verifies its CRC
        return result
    need(src.is_dir(), "input must be a standalone package directory or ZIP")
    result = {}
    total = entries = 0
    for directory, dirs, names in os.walk(src, followlinks=False):
        need(len(Path(directory).relative_to(src).parts) <= 4, "directory depth limit")
        for name in dirs + names:
            entries += 1
            need(entries <= MAX_ENTRIES, "directory entry count limit")
            p = Path(directory) / name
            need(not p.is_symlink(), "symlink in package: " + str(p.relative_to(src)))
        for name in names:
            rel = (Path(directory) / name).relative_to(src).as_posix()
            data = read_file(src, rel)
            total += len(data)
            need(total <= MAX_TOTAL, "directory total size limit")
            result[rel] = data
    return result


def prose(text):
    """Ignore fenced/inline code; the supported Markdown subset is documented."""
    lines = []; fence = None
    for line in text.splitlines():
        m = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if m:
            mark = m[1]
            if fence is None: fence = (mark[0], len(mark))
            elif mark[0] == fence[0] and len(mark) >= fence[1]: fence = None
            lines.append(""); continue
        lines.append("" if fence else re.sub(r"(`+).*?\1", "", line))
    return "\n".join(lines)


def anchors(text):
    found = set(); counts = {}
    for line in prose(text).splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not m: continue
        slug = "".join(c for c in m[1].lower() if c.isalnum() or c in " _-").replace(" ", "-")
        n = counts.get(slug, 0); counts[slug] = n + 1
        found.add(slug + ("-" + str(n) if n else ""))
    return found


def check_links(texts):
    count = 0
    for name, text in texts.items():
        if not name.endswith(".md"): continue
        body = prose(text)
        refs = {m[1].strip().casefold(): m[2] for m in re.finditer(r"(?m)^\s*\[([^\]]+)\]:\s*(\S+)", body)}
        targets = [m[1] for m in re.finditer(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", body)]
        for m in re.finditer(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]", body):
            label = (m[2] or m[1]).strip().casefold()
            need(label in refs, f"undefined reference: {name}: {label}")
            targets.append(refs[label])
        for ref in targets:
            ref = ref.strip()
            ref = ref[1:ref.index(">")] if ref.startswith("<") and ">" in ref else (ref.split()[0] if ref else "")
            url = urlsplit(ref)
            if url.scheme or url.netloc: continue
            path = unquote(url.path)
            need(not path.startswith("/") and "\\" not in path and ":" not in path,
                 f"unsafe local link: {name}: {ref}")
            parts = name.split("/")[:-1] if path else name.split("/")
            for part in path.split("/") if path else []:
                if part == "..":
                    need(bool(parts), f"link above root: {name}: {ref}"); parts.pop()
                elif part not in ("", "."): parts.append(part)
            dest = "/".join(parts)
            need(dest in texts or any(k.startswith(dest.rstrip("/") + "/") for k in texts),
                 f"missing link: {name}: {ref}")
            if url.fragment:
                need(dest in texts and dest.endswith(".md") and unquote(url.fragment) in anchors(texts[dest]),
                     f"missing heading: {name}: {ref}")
            count += 1
    need(count > 0, "no local links detected")
    return f"{count} local links/anchors resolve"


def package_checks(src):
    files = load(src)
    need(set(files) == EXPECTED, "package files differ: missing=" + str(sorted(EXPECTED-set(files))) +
         "; extra=" + str(sorted(set(files)-EXPECTED)))
    texts = {name: data.decode("utf-8-sig") for name, data in files.items()}
    need(all(text.strip() for text in texts.values()), "empty source file")
    need(texts["README.md"].splitlines()[0] == "# Project Workflow Standard — " + VERSION, "README version mismatch")
    need(re.search(r"Редакция комплекта:\s*\*\*" + re.escape(VERSION) + r"\*\*", texts["TESTING-LEVELS.md"]), "testing version mismatch")
    headings = re.findall(r"^## (.+)$", texts["CHANGELOG.md"], re.M)
    need(headings and headings[0].startswith(VERSION + " —"), "current changelog entry mismatch")
    need(texts["VALIDATION.md"].splitlines()[0] == "# Проверка стандарта — " + VERSION, "validation version mismatch")
    # Limited presence checks, deliberately NOT advertised as semantic validation.
    markers = {"AGENTS.md": ["Light", "Full", "TESTING-LEVELS.md", "разрешение", "пользовательский diff"],
               "TESTING-LEVELS.md": ["L1", "L2", "L3", "L4", "L5", "EXC-ID", "не переносится автоматически"],
               "templates/PLAN.md": ["REQ-ID"], "templates/VERIFICATION.md": ["REQ-ID"],
               "templates/RELEASE.md": ["EXC-ID"], "templates/CONTINUATION.md": ["Одно следующее действие"]}
    for name, words in markers.items():
        for word in words: need(word in texts[name], f"missing selected marker: {name}: {word}")
    preserved = {
        "AGENTS.md": ["режимы **документирования**"],
        "TESTING-LEVELS.md": ["не строгость проверок", "воспроизведён либо ограничение воспроизведения",
            "не** доказывает устранение исторической причины", "**«без исключений»**",
            "**«с исключениями: EXC-ID…»**", "Gate с применимым активным исключением", "а не «успех»"],
        "templates/VERIFICATION.md": ["либо** подтверждённые факты"],
        "examples/02-bug-traceability.md": ["**Mock подтверждает только моделируемую область**"],
        "templates/RELEASE.md": ["с исключениями"],
        "README.md": ["не подтверждённое улучшение"],
    }
    for name, words in preserved.items():
        for word in words: need(word in texts[name], f"missing preserved marker: {name}: {word}")
    tree = ast.parse(texts["tools/check_standard.py"])
    versions = [node.value.value for node in tree.body if isinstance(node, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets) and
                isinstance(node.value, ast.Constant)]
    need(versions == [VERSION], "packaged checker version mismatch")
    return {"files": len(files), "bytes": sum(map(len, files.values())), "links": check_links(texts)}


def nonempty(value, name):
    need(isinstance(value, str) and bool(value.strip()), name + " must be nonempty text")
    return value


def timestamp(value):
    result = datetime.fromisoformat(nonempty(value, "timestamp").replace("Z", "+00:00"))
    need(result.tzinfo is not None, "timestamp must contain timezone")
    return result


def unique_pairs(pairs):
    d = {}
    for k, v in pairs:
        need(k not in d, "duplicate JSON key: " + k); d[k] = v
    return d


def index(items, label):
    need(isinstance(items, list) and len(items) <= 256, label + " must be a bounded list")
    out = {}
    for item in items:
        need(isinstance(item, dict), label + " item must be an object")
        key = nonempty(item.get("id"), label + " id")
        need(key not in out, "duplicate " + label + " id: " + key); out[key] = item
    return out


def record_checks(path, now):
    raw = read_file(path.parent, path.name)
    d = json.loads(raw, object_pairs_hook=unique_pairs,
                   parse_constant=lambda s: (_ for _ in ()).throw(Invalid("nonfinite JSON: " + s)))
    need(isinstance(d, dict) and type(d.get("schema")) is int and d["schema"] == 1, "record schema must be 1")
    subject = nonempty(d.get("candidate"), "candidate")
    need(re.fullmatch(r"(?:git:[0-9a-f]{40}|sha256:[0-9a-f]{64})", subject), "invalid candidate identity")
    environment = nonempty(d.get("environment"), "environment")
    checks = index(d.get("checks"), "check"); requirements = index(d.get("requirements"), "requirement")
    exceptions = index(d.get("exceptions", []), "exception")
    need(type(d.get("l4")) is bool, "l4 must be boolean")
    for cid, c in checks.items():
        need(c.get("status") in ("pass", "fail", "not_run", "unavailable", "not_applicable"), cid + ": invalid status")
        need(c.get("level") in ("L1", "L2", "L3", "L4", "L5"), cid + ": invalid level")
        need(c.get("kind") in ("static", "build", "unit", "integration", "ui", "device", "ci", "delivery"), cid + ": invalid kind")
        need(type(c.get("required")) is bool, cid + ": required must be boolean")
        need(c.get("candidate") == subject, cid + ": stale candidate")
        if c["status"] == "pass":
            need(c.get("execution") == "actual", cid + ": success requires actual execution")
            nonempty(c.get("command"), cid + ": command/actions")
            evidence = c.get("evidence")
            need(isinstance(evidence, list) and 0 < len(evidence) <= 32, cid + ": missing/big evidence list")
            for e in evidence:
                need(isinstance(e, dict), cid + ": evidence must be object")
                b = read_file(path.parent, nonempty(e.get("path"), "evidence path"), MAX_TOTAL)
                need(hashlib.sha256(b).hexdigest() == e.get("sha256"), cid + ": evidence hash mismatch")
            need(not c.get("exception"), cid + ": exception cannot be labeled pass")
        else:
            nonempty(c.get("reason"), cid + ": reason")
    for rid, r in requirements.items():
        need(r.get("status") in ("done", "partial", "blocked", "excluded", "not_assessed", "in_progress"), rid + ": invalid requirement status")
        ids = r.get("checks", [])
        need(isinstance(ids, list) and all(isinstance(i, str) and i in checks for i in ids), rid + ": unknown checks")
        if r["status"] == "done":
            need(ids and all(checks[i]["status"] == "pass" for i in ids), rid + ": done lacks passing checks")
        elif r["status"] == "excluded": nonempty(r.get("approval"), rid + ": owner decision source")
        else: nonempty(r.get("reason"), rid + ": remainder")
    for cid, c in checks.items():
        if c.get("exception"):
            e = exceptions.get(c["exception"])
            need(e is not None, cid + ": unknown exception")
            need(e.get("status") == "active" and e.get("check") == cid and e.get("candidate") == subject and
                 e.get("environment") == environment and timestamp(e.get("expires")) > now,
                 cid + ": expired/out-of-scope exception")
            for k in ("approved_by", "approval", "reason", "risk", "compensation"): nonempty(e.get(k), "exception " + k)
    if d["l4"]:
        need(checks and requirements, "L4 needs checks and requirements")
        need(all(r["status"] in ("done", "excluded") for r in requirements.values()), "L4 has unresolved requirements")
        need(all(not c["required"] or c["status"] == "pass" or c.get("exception") for c in checks.values()), "L4 has open required gate")
    claims = d.get("claims", [])
    kinds = {"device_tested": "device", "ui_tested": "ui", "ci_executed": "ci"}
    need(isinstance(claims, list) and all(isinstance(k, str) and k in kinds for k in claims), "unknown claim")
    for claim in claims:
        need(any(c["status"] == "pass" and c["kind"] == kinds[claim] for c in checks.values()), claim + ": missing matching executed check")
    delivery = d.get("delivery")
    need(isinstance(delivery, dict) and delivery.get("status") in ("not_started", "prepared", "published", "verified", "failed", "recovery_required"), "invalid delivery status")
    if delivery["status"] in ("published", "verified"):
        nonempty(delivery.get("permission"), "delivery permission source")
        need(d["l4"] and delivery.get("candidate") == subject, "delivery lacks L4/exact candidate")
    if delivery["status"] == "verified":
        need(any(c["level"] == "L5" and c["kind"] == "delivery" and c["status"] == "pass" for c in checks.values()), "verified delivery lacks L5")
    return {"checks": len(checks), "requirements": len(requirements), "evaluated_at": now.isoformat(),
            "limitation": "declared evidence consistency; no authorization/log-truth/coverage attestation"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", type=Path, default=Path("."))
    p.add_argument("--record", type=Path, help="optional schema-1 JSON record with local hashed evidence")
    p.add_argument("--at", help="timezone-qualified evaluation time; default UTC now")
    p.add_argument("--json", action="store_true", help="machine-readable result")
    args = p.parse_args()
    try:
        result = {"package": package_checks(args.path)}
        if args.record:
            result["record"] = record_checks(args.record, timestamp(args.at) if args.at else datetime.now(timezone.utc))
        result.update(ok=True, agent_behavior_evaluated=False)
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError, SyntaxError, RuntimeError,
            EOFError, zipfile.BadZipFile, zlib.error) as exc:
        result = {"ok": False, "error": str(exc), "agent_behavior_evaluated": False}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
          ("PASS " if result["ok"] else "FAIL ") + json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
