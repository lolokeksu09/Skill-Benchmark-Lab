"""Single-control offline Web-code pilot over local Termux llama-server."""
import argparse
import hashlib
import json
from pathlib import Path
from evaluator.candidate_checks import check_candidate
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "web-fixture-repair"

def fingerprint(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def prompt_for_fixture(root):
    base = root / "benchmarks/fixtures/web/baseline"
    js = (base / "feed.mjs").read_text(encoding="utf-8")
    css = (base / "feed.css").read_text(encoding="utf-8")
    return (
        "Fix three defects in the following two-file web fixture. "
        "Keep the renderPost export, article/h2, save button and original styling intent. "
        "Tests require: (1) HTML-escape user-controlled post.title including <, > and &; "
        "(2) add aria-label=\"Save post\" on the existing icon-only button; "
        "(3) CSS .feed has max-width: 100% for responsive layout. "
        "Return ONLY a JSON object with exactly two string keys feed.mjs and feed.css; "
        "each value must contain the complete corrected file. No markdown fences. "
        "No third-party packages or other files. End the reply after JSON.\n\n"
        "--- feed.mjs ---\n" + js + "\n--- feed.css ---\n" + css + "\n/no_think"
    )

def request_completion(base_url, prompt, max_tokens, timeout):
    base_url = base_url.rstrip("/")
    if base_url not in ("http://127.0.0.1:8080", "http://localhost:8080"):
        raise ValueError("Only a local llama-server at port 8080 is allowed")
    payload = json.dumps({
        "messages": [{"role": "system", "content": "You are a code editor. Return only the requested JSON. Never claim tests have run."},
                     {"role": "user", "content": prompt}],
        "temperature": 0.2, "max_tokens": max_tokens, "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base_url + "/v1/chat/completions",
                                 data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data.get("choices"), list) or not data["choices"]:
        raise ValueError("llama-server response has no choices")
    output = data["choices"][0].get("message", {}).get("content")
    if not isinstance(output, str):
        raise ValueError("llama-server response has no text content")
    return data, output

def parse_candidate(output):
    try:
        obj = json.loads(output)
    except (ValueError, TypeError):
        return False, "output is not a JSON object"
    if (not isinstance(obj, dict) or set(obj) != {"feed.mjs", "feed.css"}
            or not all(isinstance(v, str) for v in obj.values())):
        return False, "expected two complete string files"
    if not obj["feed.mjs"].strip() or not obj["feed.css"].strip():
        return False, "empty file output"
    return True, obj

def run_once(root, output_dir, results_path, base_url, max_tokens, timeout, run_id):
    prompt = prompt_for_fixture(root)
    start = time.monotonic()
    record = {
        "scenario_id": CASE_ID, "variant": "control", "run_id": run_id,
        "duration_seconds": None, "total_tokens": None, "review": None,
        "model": None, "prompt_sha256": fingerprint(prompt),
        "candidate_valid_json": False, "candidate_path": None, "status": "error",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / (run_id + ".txt")
    try:
        data, output = request_completion(base_url, prompt, max_tokens, timeout)
        raw_path.write_text(output, encoding="utf-8")
        ok, candidate = parse_candidate(output)
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        try:
            relative = str(raw_path.relative_to(root))
        except ValueError:
            relative = str(raw_path)
        record.update(
            model=data.get("model"), total_tokens=usage.get("total_tokens"),
            prompt_tokens=usage.get("prompt_tokens"), completion_tokens=usage.get("completion_tokens"),
            finish_reason=data["choices"][0].get("finish_reason"),
            candidate_valid_json=ok, status="candidate_saved" if ok else "invalid_candidate",
            candidate_path=relative, error=None if ok else candidate,
            static_preflight=check_candidate(candidate) if ok else None,
            runtime_tests_executed=False, runtime_tests_passed=None,
        )
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        record["error"] = str(error)[:500]
    finally:
        record["duration_seconds"] = round(time.monotonic() - start, 3)
        results_path.parent.mkdir(parents=True, exist_ok=True)
        with results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record

def main():
    parser = argparse.ArgumentParser(description="Termux Qwen3-8B Web repair pilot, control mode")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--max-tokens", type=int, default=400)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output", default="results/raw/local-qwen-web-pilot.jsonl")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 3 or not 16 <= args.max_tokens <= 1024:
        parser.error("--repeats must be 1-3, --max-tokens must be 16-1024")
    output_file = ROOT / args.output
    if output_file.exists():
        parser.error("output exists, will not overwrite: " + str(output_file))
    run_dir = ROOT / "results/raw/local-qwen-web-candidates"
    for number in range(1, args.repeats + 1):
        rec = run_once(ROOT, run_dir, output_file, args.base_url,
                       args.max_tokens, args.timeout, "trial-%03d" % number)
        print(json.dumps({key: rec.get(key) for key in
              ("run_id", "status", "duration_seconds", "total_tokens", "finish_reason", "static_preflight", "error")},
              ensure_ascii=False))
    print("Local results: " + str(output_file))
    print("Generated JavaScript NOT executed. Inspect candidates before isolated tests.")

if __name__ == "__main__":
    main()
