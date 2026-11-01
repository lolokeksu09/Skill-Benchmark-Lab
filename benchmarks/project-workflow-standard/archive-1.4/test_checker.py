"""Public regression tests. Only disposable copies of the standard are mutated."""
from pathlib import Path
import copy
import hashlib
import json
import os
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "candidate-v1.4-rc4"
CHECKER = Path(os.environ.get("PWS_CHECKER", PACKAGE / "tools/check_standard.py"))


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.kit = self.root / "kit"
        for p in PACKAGE.rglob("*"):
            if p.is_file():
                dest = self.kit / p.relative_to(PACKAGE)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(p.read_bytes())

    def tearDown(self):
        self.tmp.cleanup()

    def run_checker(self, path=None, *extra, optimized=False):
        return subprocess.run([sys.executable] + (["-O"] if optimized else []) +
                              [str(CHECKER), str(path or self.kit), *extra],
                              capture_output=True, text=True, timeout=10)

    def reject(self, path=None, *extra, optimized=False):
        r = self.run_checker(path, *extra, optimized=optimized)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        return r

    def archive(self, extra=()):
        p = self.root / "kit.zip"
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
            for f in self.kit.rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(self.kit).as_posix())
            for name, data in extra:
                z.writestr(name, data)
        return p

    def test_valid_directory(self):
        r = self.run_checker()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_valid_zip(self):
        r = self.run_checker(self.archive())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_optimization_cannot_disable_validation(self):
        (self.kit / "AGENTS.md").write_text("rules removed\n")
        self.reject(optimized=True)

    def test_empty_readme_under_optimization_is_clean_failure(self):
        (self.kit / "README.md").write_text("")
        self.reject(optimized=True)

    def test_missing_file(self):
        (self.kit / "PROJECT.md").unlink()
        self.reject()

    def test_extra_payload(self):
        (self.kit / "payload.bin").write_bytes(b"unreviewed")
        self.reject()

    def test_directory_symlink(self):
        target = self.root / "outside.md"
        target.write_bytes((self.kit / "PROJECT.md").read_bytes())
        (self.kit / "PROJECT.md").unlink()
        (self.kit / "PROJECT.md").symlink_to(target)
        self.reject()

    def test_zip_symlink(self):
        p = self.archive()
        with zipfile.ZipFile(p, "a") as z:
            info = zipfile.ZipInfo("outside")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "/etc/hostname")
        self.reject(p)

    def test_zip_nul_name_cannot_alias_required_file(self):
        p = self.root / "nul.zip"
        with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as z:
            for f in self.kit.rglob("*"):
                if f.is_file():
                    name = f.relative_to(self.kit).as_posix()
                    z.writestr(name + "AA" if name == "AGENTS.md" else name, f.read_bytes())
        p.write_bytes(p.read_bytes().replace(b"AGENTS.mdAA", b"AGENTS.md\x00A"))
        self.reject(p)

    def test_corrupt_deflate_returns_machine_readable_failure(self):
        p = self.archive()
        with zipfile.ZipFile(p) as z:
            offset = z.infolist()[0].header_offset
        data = bytearray(p.read_bytes())
        name_len, extra_len = struct.unpack_from("<HH", data, offset + 26)
        data[offset + 30 + name_len + extra_len] = 0xff
        p.write_bytes(data)
        r = self.reject(p, "--json")
        self.assertFalse(json.loads(r.stdout)["ok"])

    def test_noncanonical_zip_paths(self):
        for path in ["../outside", "/outside", "C:/outside", "a\\outside", "./outside", "a//outside"]:
            with self.subTest(path=path):
                self.reject(self.archive([(path, b"x")]))

    def test_oversized_source(self):
        (self.kit / "PROJECT.md").write_bytes(b"x" * (256 * 1024 + 1))
        self.reject()

    def test_oversized_zip_source(self):
        (self.kit / "PROJECT.md").write_bytes(b"x" * (256 * 1024 + 1))
        self.reject(self.archive())

    def test_broken_fragment(self):
        with (self.kit / "README.md").open("a") as f:
            f.write("\n[bad](AGENTS.md#missing-heading)\n")
        self.reject()

    def test_broken_image(self):
        with (self.kit / "README.md").open("a") as f:
            f.write("\n![missing](lost.png)\n")
        self.reject()

    def test_links_in_fences_are_examples(self):
        with (self.kit / "README.md").open("a") as f:
            f.write("\n```md\n[example](absent.md)\n```\n")
        r = self.run_checker()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_empty_link_destination_does_not_crash(self):
        with (self.kit / "README.md").open("a") as f:
            f.write("\n[self]( )\n")
        r = self.run_checker(None, "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout)["ok"])

    def test_current_changelog_version_is_first(self):
        p = self.kit / "CHANGELOG.md"
        p.write_text(p.read_text().replace("# История изменений", "# История изменений\n\n## 9.9 — newer", 1))
        self.reject()

    def test_validation_title_version(self):
        p = self.kit / "VALIDATION.md"
        p.write_text(p.read_text().replace("# Проверка стандарта — 1.4-rc4", "# Проверка стандарта — 9.9", 1))
        self.reject()

    def test_script_version_mismatch(self):
        p = self.kit / "tools/check_standard.py"
        p.write_text(p.read_text().replace('VERSION = "1.4-rc4"', 'VERSION = "9.9"', 1))
        self.reject()

    def record(self):
        log = self.root / "test.log"
        log.write_text("exit=0\n")
        evidence = {"path": "test.log", "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
        subject = "sha256:" + "a" * 64
        return {"schema": 1, "candidate": subject, "environment": "isolated",
                "checks": [{"id": "T1", "level": "L2", "kind": "unit", "required": True,
                            "status": "pass", "candidate": subject, "command": "python -m unittest",
                            "execution": "actual", "evidence": [evidence]}],
                "requirements": [{"id": "REQ-001", "status": "done", "checks": ["T1"]}],
                "exceptions": [], "claims": [], "l4": True,
                "delivery": {"status": "prepared"}}

    def check_record(self, data, valid=False):
        p = self.root / "record.json"
        p.write_text(json.dumps(data))
        args = ("--record", str(p), "--at", "2026-11-01T12:00:00+00:00")
        if valid:
            r = self.run_checker(None, *args)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        else:
            self.reject(None, *args)

    def test_valid_evidence(self):
        self.check_record(self.record(), valid=True)

    def test_skipped_gate_blocks_l4(self):
        d = self.record(); d["checks"][0].update(status="not_run", reason="skipped")
        d["requirements"][0].update(status="excluded", approval="owner scope decision")
        self.check_record(d)

    def test_success_requires_actual_execution(self):
        d = self.record(); d["checks"][0]["execution"] = "dry_run"
        self.check_record(d)

    def test_stale_revision(self):
        d = self.record(); d["checks"][0]["candidate"] = "sha256:" + "b" * 64
        self.check_record(d)

    def test_evidence_hash(self):
        d = self.record(); d["checks"][0]["evidence"][0]["sha256"] = "0" * 64
        self.check_record(d)

    def test_evidence_symlink(self):
        d = self.record(); (self.root / "link.log").symlink_to(self.root / "test.log")
        d["checks"][0]["evidence"][0]["path"] = "link.log"
        self.check_record(d)

    def test_evidence_traversal(self):
        d = self.record(); d["checks"][0]["evidence"][0]["path"] = "../test.log"
        self.check_record(d)

    def test_build_is_not_device_test(self):
        d = self.record(); d["checks"][0]["kind"] = "build"; d["claims"] = ["device_tested"]
        self.check_record(d)

    def test_unit_is_not_ui(self):
        d = self.record(); d["claims"] = ["ui_tested"]
        self.check_record(d)

    def test_unresolved_requirement_blocks_l4(self):
        d = self.record(); d["requirements"][0].update(status="blocked", reason="conflict")
        self.check_record(d)

    def test_regression_blocks_done_requirement(self):
        d = self.record(); c = copy.deepcopy(d["checks"][0]); c.update(id="T2", status="fail", reason="regression")
        d["checks"].append(c); d["requirements"][0]["checks"].append("T2")
        self.check_record(d)

    def exception_record(self):
        d = self.record(); d["checks"][0].update(status="unavailable", exception="EXC-001", reason="offline")
        d["requirements"][0].update(status="excluded", approval="owner decision 01")
        d["exceptions"] = [{"id": "EXC-001", "check": "T1", "candidate": d["candidate"],
                            "environment": d["environment"], "status": "active",
                            "approved_by": "owner", "approval": "decision 01", "reason": "offline",
                            "risk": "unverified integration", "compensation": "none",
                            "expires": "2026-11-02T00:00:00+00:00"}]
        return d

    def test_active_exception_preserves_unavailable(self):
        self.check_record(self.exception_record(), valid=True)

    def test_expired_exception(self):
        d = self.exception_record(); d["exceptions"][0]["expires"] = "2026-10-31T00:00:00+00:00"
        self.check_record(d)

    def test_exception_wrong_candidate(self):
        d = self.exception_record(); d["exceptions"][0]["candidate"] = "sha256:" + "c" * 64
        self.check_record(d)

    def test_publication_requires_permission(self):
        d = self.record(); d["delivery"].update(status="published", candidate=d["candidate"])
        self.check_record(d)

    def test_verified_delivery_requires_l5(self):
        d = self.record(); d["delivery"].update(status="verified", candidate=d["candidate"], permission="owner")
        self.check_record(d)

    def test_published_unverified_is_valid_separate_state(self):
        d = self.record(); d["delivery"].update(status="published", candidate=d["candidate"], permission="owner decision 2")
        self.check_record(d, valid=True)

    def test_verified_delivery_positive(self):
        d = self.record(); c = copy.deepcopy(d["checks"][0]); c.update(id="L5", level="L5", kind="delivery")
        d["checks"].append(c)
        d["delivery"].update(status="verified", candidate=d["candidate"], permission="owner decision 2")
        self.check_record(d, valid=True)

    def test_blocked_honest_partial_record_is_valid(self):
        d = self.record(); d["l4"] = False
        d["checks"][0].update(status="unavailable", reason="service unavailable")
        d["requirements"][0].update(status="blocked", reason="integration not checked")
        self.check_record(d, valid=True)

    def test_unknown_status_and_unknown_claim_fail_closed(self):
        for field in ["status", "claims"]:
            d = self.record()
            if field == "status": d["checks"][0]["status"] = "success-ish"
            else: d["claims"] = ["all_tested"]
            self.check_record(d)

    def test_duplicate_ids(self):
        d = self.record(); d["checks"].append(copy.deepcopy(d["checks"][0]))
        self.check_record(d)


if __name__ == "__main__":
    unittest.main()
