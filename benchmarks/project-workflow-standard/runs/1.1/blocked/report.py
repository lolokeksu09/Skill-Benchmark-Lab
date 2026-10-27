import json
import sys


STATUS_LABEL="Моя панель"


def summarize(checks):
    counts = {
        status: sum(check["status"] == status for check in checks)
        for status in ("success", "failure", "skipped")
    }
    mandatory = [check for check in checks if check.get("mandatory", False)]
    ready = bool(mandatory) and all(check["status"] == "success" for check in mandatory)
    return {"counts": counts, "ready": ready}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as input_file:
        print(json.dumps(summarize(json.load(input_file))))
