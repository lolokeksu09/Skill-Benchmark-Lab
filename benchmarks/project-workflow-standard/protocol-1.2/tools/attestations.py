"""SSH Ed25519 signature verification for runner and independent-review evidence."""
from __future__ import annotations
import hashlib, importlib.util, json, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("safe_io", ROOT / "tools/safe_io.py")
safe = importlib.util.module_from_spec(spec); spec.loader.exec_module(safe)

def canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def file_hash(path: Path) -> str:
    return hashlib.sha256(safe.read_bytes(path.parent, path.name, 4 * 1024 * 1024)).hexdigest()

def verify_detached(payload_path: Path, signature_path: Path, allowed_signers: Path,
                    identity: str, namespace: str) -> tuple[bool, str]:
    if not shutil.which("ssh-keygen"):
        return False, "ssh-keygen unavailable"
    try:
        payload = safe.read_bytes(payload_path.parent, payload_path.name, 4 * 1024 * 1024)
        # Validate these as regular files too; ssh-keygen must not follow a candidate link.
        safe.read_bytes(signature_path.parent, signature_path.name, 1024 * 1024)
        safe.read_bytes(allowed_signers.parent, allowed_signers.name, 1024 * 1024)
        proc = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(allowed_signers),
                               "-I", identity, "-n", namespace, "-s", str(signature_path)],
                              input=payload, capture_output=True, timeout=10)
        return proc.returncode == 0, proc.stderr.decode("utf-8", "replace").strip()
    except Exception as exc:
        return False, repr(exc)

def load_signed(payload_path: Path, signature_path: Path, allowed_signers: Path,
                identity: str, namespace: str, kind: str) -> tuple[dict | None, dict]:
    ok, detail = verify_detached(payload_path, signature_path, allowed_signers, identity, namespace)
    if not ok:
        return None, {"ok": False, "identity": identity, "detail": detail}
    try:
        payload = json.loads(safe.read_text(payload_path.parent, payload_path.name, 4 * 1024 * 1024))
        if payload.get("kind") != kind:
            return None, {"ok": False, "identity": identity, "detail": "wrong attestation kind"}
        return payload, {"ok": True, "identity": identity, "payload_sha256": file_hash(payload_path)}
    except Exception as exc:
        return None, {"ok": False, "identity": identity, "detail": repr(exc)}
