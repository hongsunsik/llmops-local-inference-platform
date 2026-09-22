"""Deterministic regression gate for the keyword model router."""

import json
from pathlib import Path

from app.config import Settings
from app.models import ChatCompletionRequest, ChatMessage
from app.routing import select_model

CASES_PATH = Path(__file__).parents[1] / "evaluation" / "routing_cases.jsonl"


def main() -> None:
    settings = Settings()
    failures = []
    for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        request = ChatCompletionRequest(messages=[ChatMessage(role="user", content=case["input"])])
        actual_model = select_model(request, settings)
        if actual_model != case["expected_model"]:
            failures.append((case["id"], case["expected_model"], actual_model))

    if failures:
        for case_id, expected, actual in failures:
            print(f"FAIL {case_id}: expected={expected} actual={actual}")
        raise SystemExit(1)

    case_count = len(CASES_PATH.read_text(encoding="utf-8").splitlines())
    print(f"PASS: {case_count} routing cases")


if __name__ == "__main__":
    main()
