import json
from pathlib import Path

from app.config import Settings
from app.models import ChatCompletionRequest, ChatMessage
from app.routing import select_model


def test_routing_evaluation_dataset() -> None:
    cases_path = Path(__file__).parents[1] / "evaluation" / "routing_cases.jsonl"
    settings = Settings()

    for line in cases_path.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        request = ChatCompletionRequest(messages=[ChatMessage(role="user", content=case["input"])])
        assert select_model(request, settings) == case["expected_model"], case["id"]
