"""Compare Qwen3 /think on control and verified DDS via the same local API.

Keep prior /no_think trial files unchanged. No generated code is executed.
"""
import argparse
import json
import re
from pathlib import Path
import time
import urllib.error
import urllib.request
from evaluator.local_llama import ROOT, fingerprint, parse_candidate, prompt_for_fixture
from evaluator.development_pilot import BASE_SYSTEM, DEFAULT_ARCHIVE, make_messages, verified_skills
from evaluator.candidate_checks import check_candidate

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"


def messages_for(variant, skills=()):
    if variant == "control":
        messages = [{"role": "system", "content": BASE_SYSTEM},
                    {"role": "user", "content": prompt_for_fixture(ROOT)}]
    elif variant == "development" and skills:
        messages = make_messages(ROOT, skills)
    else:
        raise ValueError("Unsupported or unverified experiment variant")
    if not messages[-1]["content"].endswith("/no_think"):
        raise ValueError("Frozen task does not end with /no_think")
    messages[-1]["content"] = messages[-1]["content"][:-len("/no_think")] + "/think"
    return messages


def final_content(message):
    content = message.get("content") or ""
    if not isinstance(content, str):
        content = ""
    separate = message.get("reasoning_content")
    reasoned = isinstance(separate, str) and bool(separate.strip())
    if re.match(r"^\s*<think>", content):
        reasoned = True
        match = re.match(r"^\s*<think>.*?</think>\s*", content, flags=re.S)
        if match:
            content = content[match.end():]
    return content.strip(), reasoned


def request_model(messages, max_tokens, timeout):
    body = json.dumps({"messages": messages, "temperature": 0.2,
                       "max_tokens": max_tokens, "stream": False},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def trial(variant, messages, archive_sha, skills, output_dir, results_file,
          run_id="trial-001", max_tokens=768, timeout=900):
    candidate_file = output_dir / (run_id + ".txt")
    raw_file = output_dir / (run_id + ".response.json")
    if candidate_file.exists() or raw_file.exists():
        raise FileExistsError("Refusing to overwrite existing trial: " + run_id)
    start = time.monotonic()
    record = {"scenario_id": "web-fixture-repair", "variant": variant,
              "experiment": "thinking_on", "run_id": run_id,
              "status": "error", "duration_seconds": None, "total_tokens": None,
              "prompt_tokens": None, "completion_tokens": None,
              "review": None, "reasoning_present": None,
              "input_sha256": fingerprint(json.dumps(messages, ensure_ascii=False)),
              "skill_archive_sha256": archive_sha,
              "active_skills": [{"name": s["name"], "sha256": s["sha256"]} for s in skills],
              "runtime_tests_executed": False, "runtime_tests_passed": None}
    try:
        data = request_model(messages, max_tokens, timeout)
        choice = data["choices"][0]
        message = choice["message"]
        content, reasoning_present = final_content(message)
        valid, candidate = parse_candidate(content)
        output_dir.mkdir(parents=True, exist_ok=True)
        with raw_file.open("x", encoding="utf-8") as handle:
            json.dump({"message": message, "usage": data.get("usage"),
                       "timings": data.get("timings"), "finish_reason": choice.get("finish_reason")},
                      handle, ensure_ascii=False, indent=2)
        with candidate_file.open("x", encoding="utf-8") as handle:
            handle.write(content)
        usage = data.get("usage") or {}
        timings = data.get("timings") or {}
        record.update(status=("candidate_saved" if valid else
                              "truncated" if choice.get("finish_reason") == "length" else
                              "invalid_candidate"),
                      model=data.get("model"), prompt_tokens=usage.get("prompt_tokens"),
                      completion_tokens=usage.get("completion_tokens"),
                      total_tokens=usage.get("total_tokens"),
                      finish_reason=choice.get("finish_reason"),
                      reasoning_present=reasoning_present,
                      prompt_processing_ms=timings.get("prompt_ms"),
                      generation_ms=timings.get("predicted_ms"),
                      candidate_valid_json=valid,
                      candidate_path=str(candidate_file),
                      raw_message_path=str(raw_file),
                      static_preflight=check_candidate(candidate) if valid else None,
                      error=None if valid else str(candidate))
    except (OSError, ValueError, KeyError, IndexError, urllib.error.URLError) as error:
        record["error"] = str(error)[:500]
    finally:
        record["duration_seconds"] = round(time.monotonic() - start, 3)
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with results_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description="Isolated Qwen /think Web benchmark")
    parser.add_argument("--variant", required=True, choices=("control", "development"))
    parser.add_argument("--trial", type=int, default=1)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    if not (1 <= args.trial <= 3 and 128 <= args.max_tokens <= 768):
        parser.error("trial must be 1-3 and max-tokens 128-768")
    skills, archive_sha = (), None
    if args.variant == "development":
        try:
            archive_sha, skills = verified_skills(args.archive)
        except (ValueError, OSError, KeyError) as error:
            parser.error("Invalid DDS archive: " + str(error))
    messages = messages_for(args.variant, skills)
    run_id = "trial-%03d" % args.trial
    result = ROOT / ("results/raw/local-qwen-web-thinking-" + args.variant + ".jsonl")
    output = ROOT / "results/raw/local-qwen-web-candidates/thinking" / args.variant
    if args.trial == 1 and result.exists():
        parser.error("Result file exists; refusing to repeat trial-001")
    if (output / (run_id + ".txt")).exists() or (output / (run_id + ".response.json")).exists():
        parser.error("Trial already exists: " + run_id)
    print("Mode:", args.variant, "Thinking: enabled", "Trial:", run_id)
    rec = trial(args.variant, messages, archive_sha, skills, output, result,
                run_id, args.max_tokens, args.timeout)
    print(json.dumps({k: rec.get(k) for k in
          ("run_id", "status", "duration_seconds", "prompt_tokens", "completion_tokens",
           "total_tokens", "finish_reason", "reasoning_present", "static_preflight", "error")},
           ensure_ascii=False))
    print("Results:", result)
    print("Generated JavaScript was NOT executed.")


if __name__ == "__main__":
    main()
