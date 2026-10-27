import json
import sys

STATUS_LABEL="Моя панель"


def summarize(checks):
    counts = {"success": 0, "failure": 0, "skipped": 0}
    mandatory_seen = False
    mandatory_success = True
    for check in checks:
        status = check["status"]
        counts[status] += 1
        if check.get("mandatory", False):
            mandatory_seen = True
            mandatory_success = mandatory_success and status == "success"
    return {"counts": counts, "ready": mandatory_seen and mandatory_success}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as input_file:
        checks = json.load(input_file)
    print(json.dumps(summarize(checks), ensure_ascii=False))
