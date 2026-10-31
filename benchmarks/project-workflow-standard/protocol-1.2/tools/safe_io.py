"""Read candidate trees without following links or accepting special files."""
from __future__ import annotations
import hashlib, json, os, stat
from pathlib import Path, PurePosixPath

DEFAULT_LIMIT = 1024 * 1024

class UnsafeFile(ValueError):
    pass

def _parts(relative: str | Path) -> list[str]:
    text = str(relative).replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or any(p in {"", ".", ".."} for p in path.parts):
        raise UnsafeFile(f"unsafe relative path: {relative!r}")
    return list(path.parts)

def _open_root(root: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    return os.open(root, flags)

def read_bytes(root: Path, relative: str | Path, limit: int = DEFAULT_LIMIT) -> bytes:
    parts = _parts(relative)
    root_fd = _open_root(root)
    fds = [root_fd]
    try:
        current = root_fd
        for part in parts[:-1]:
            flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
            current = os.open(part, flags, dir_fd=current)
            fds.append(current)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(parts[-1], flags, dir_fd=current)
        fds.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise UnsafeFile(f"not a regular file: {relative}")
        if before.st_size > limit:
            raise UnsafeFile(f"file exceeds {limit} bytes: {relative}")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk); total += len(chunk)
            if total > limit:
                raise UnsafeFile(f"file grew beyond {limit} bytes: {relative}")
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise UnsafeFile(f"file changed while being read: {relative}")
        return b"".join(chunks)
    finally:
        for fd in reversed(fds):
            os.close(fd)

def read_text(root: Path, relative: str | Path, limit: int = DEFAULT_LIMIT) -> str:
    return read_bytes(root, relative, limit).decode("utf-8")

def read_json(root: Path, relative: str | Path, limit: int = DEFAULT_LIMIT):
    return json.loads(read_text(root, relative, limit))

def snapshot(root: Path, exclude: tuple[str, ...] = (), limit: int = DEFAULT_LIMIT) -> dict[str, str]:
    root = Path(root)
    root_fd = _open_root(root)
    os.close(root_fd)
    result: dict[str, str] = {}
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in list(dirnames):
            path = directory_path / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise UnsafeFile(f"unsafe directory entry: {path.relative_to(root)}")
        for name in filenames:
            path = directory_path / name
            rel = path.relative_to(root).as_posix()
            if rel in exclude or any(rel.startswith(prefix.rstrip("/") + "/") for prefix in exclude):
                continue
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                raise UnsafeFile(f"non-regular candidate file: {rel}")
            result[rel] = hashlib.sha256(read_bytes(root, rel, limit)).hexdigest()
    return dict(sorted(result.items()))

def tree_hash(root: Path, exclude: tuple[str, ...] = ()) -> str:
    entries = snapshot(root, exclude)
    h = hashlib.sha256()
    for name, digest in entries.items():
        h.update(name.encode("utf-8")); h.update(b"\0"); h.update(digest.encode("ascii")); h.update(b"\0")
    return h.hexdigest()
