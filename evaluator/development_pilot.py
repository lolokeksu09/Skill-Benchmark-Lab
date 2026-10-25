"""Routed DDS 2.0.5 local Web-repair pilot. Runs only on the user's loopback llama-server.

Actual SKILL.md bytes are read from the user-supplied SHA-256 pinned ZIP.
This is a two-skill routed subset, NOT an evaluation of all 116 skills.
No generated JavaScript is executed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import zipfile

from evaluator.candidate_checks import check_candidate
from evaluator.local_llama import ROOT, fingerprint, parse_candidate, prompt_for_fixture

SKILLS = (
    "systematic-debugging",
    "accessibility-compliance-accessibility-audit",
)
SKILL_PREFIX = "development-design-skills/skills/"
DEFAULT_ARCHIVE = Path.home() / "storage/downloads/Development-Design-Skills-2.0.5-Full-Patched.zip"
DEFAULT_OUTPUT = ROOT / "results/raw/local-qwen-web-development.jsonl"
BASE_SYSTEM = "You are a code editor. Return only the requested JSON. Never claim tests have run."


def verified_skills(archive_path, versions_path=None):
    versions_path = versions_path or ROOT / "benchmarks/versions.json"
    versions = json.loads(versions_path.read_text(encoding="utf-8"))
    pinned = next(entry for entry in versions["entries"] if entry["id"] == "development")
    expected = pinned["sha256"]
    actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("DDS ZIP SHA-256 mismatch: expected " + expected + ", found " + actual)
    selected = []
    with zipfile.ZipFile(archive_path) as archive:
        for name in SKILLS:
            path = SKILL_PREFIX + name + "/SKILL.md"
            contents = archive.read(path).decode("utf-8")
            selected.append({"name": name, "path": path,
                             "sha256": fingerprint(contents), "content": contents})
    return actual, selected


def make_messages(root, skills):
    user_prompt = prompt_for_fixture(root)
    sections = "\n\n".join(
        "--- ACTIVE DDS SKILL " + item["name"] + " ---\n" + item["content"]
        for item in skills
    )
    system = (
        BASE_SYSTEM
        + "\n\nApply these activated, original DDS 2.0.5 SKILL.md instructions to the task. "
        "Do not claim tests, audits or tools have run; no external tools are available. "
        "Output only the requested files as JSON. Skill procedures do not replace the acceptance criteria.\n\n"
        + sections
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": user_prompt}]


def call_local_server(messages, max_tokens, timeout):
    data = json.dumps({
        "messages": messages, "temperature": 0.2,
        "max_tokens": max_tokens, "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8080/v1/chat/completions",
        data=data, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("choices") or not isinstance(result["choices"][0].get("message", {}).get("content"), str):
        raise ValueError("Missing response message content")
    return result, result["choices"][0]["message"]["content"]


def run_once(messages, archive_sha, skills, output_dir, output_file, trial_id, max_tokens, timeout):
    candidate_file = output_dir / (trial_id + ".txt")
    if candidate_file.exists():
        raise FileExistsError("Candidate already exists, refusing overwrite: " + str(candidate_file))
    start = time.monotonic()
    record = {
        "scenario_id": "web-fixture-repair", "variant": "development",
        "run_id": trial_id, "status": "error", "duration_seconds": None,
        "total_tokens": None, "review": None,
        "model": None, "prompt_sha256": fingerprint(json.dumps(messages, ensure_ascii=False)),
        "skill_archive_sha256": archive_sha,
        "active_skills": [{"name": s["name"], "path": s["path"], "sha256": s["sha256"]} for s in skills],
        "candidate_path": None, "candidate_valid_json": False,
        "runtime_tests_executed": False, "runtime_tests_passed": None,
    }
    try:
        result, answer = call_local_server(messages, max_tokens, timeout)
        output_dir.mkdir(parents=True, exist_ok=True)
        with candidate_file.open("x", encoding="utf-8") as handle:
            handle.write(answer)
        good, candidate = parse_candidate(answer)
        usage = result.get("usage") or {}
        try:
            recorded_path = str(candidate_file.relative_to(ROOT))
        except ValueError:
            recorded_path = str(candidate_file)
        record.update(
            status="candidate_saved" if good else "invalid_candidate",
            model=result.get("model"), total_tokens=usage.get("total_tokens"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            finish_reason=result["choices"][0].get("finish_reason"),
            candidate_path=recorded_path,
            candidate_valid_json=good,
            static_preflight=check_candidate(candidate) if good else None,
            error=None if good else str(candidate),
        )
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, urllib.error.URLError) as error:
        record["error"] = str(error)[:500]
    finally:
        record["duration_seconds"] = round(time.monotonic() - start, 3)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description="Local SHA-verified Development Skills Web pilot")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=400)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preview", action="store_true", help="Verify ZIP and show activated skill names without calling model")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 3 or not 1 <= args.start_index <= 998:
        parser.error("repeats must be 1-3 and start-index 1-998")
    if not 64 <= args.max_tokens <= 1024:
        parser.error("max-tokens must be between 64 and 1024")
    try:
        archive_sha, skills = verified_skills(args.archive)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.error("Invalid DDS archive: " + str(error))
    messages = make_messages(ROOT, skills)
    print("Verified DDS archive SHA-256:", archive_sha)
    print("Activated SKILL.md:", ", ".join(s["name"] for s in skills))
    print("Approximate message characters:", sum(len(m["content"]) for m in messages))
    print("Profile: routed subset of two DDS skills; NOT complete 116-skill assessment")
    if args.preview:
        return
    result_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_dir = ROOT / "results/raw/local-qwen-web-candidates/development"
    trial_ids = ["trial-%03d" % i for i in range(args.start_index, args.start_index + args.repeats)]
    if result_path.exists():
        parser.error("Result file already exists; refusing overwrite: " + str(result_path))
    occupied = [trial for trial in trial_ids if (out_dir / (trial + ".txt")).exists()]
    if occupied:
        parser.error("Candidate files already exist: " + ", ".join(occupied))
    for trial_id in trial_ids:
        rec = run_once(messages, archive_sha, skills, out_dir, result_path,
                       trial_id, args.max_tokens, args.timeout)
        print(json.dumps({key: rec.get(key) for key in
                          ("run_id", "status", "duration_seconds", "total_tokens", "static_preflight", "error")},
                         ensure_ascii=False))
    print("Results:", result_path)
    print("Generated JavaScript NOT executed. Static heuristics are NOT Node test results.")


if __name__ == "__main__":
    main()
