from app.config import Settings
from app.models import ChatCompletionRequest

CODING_TERMS = {
    "code",
    "coding",
    "bug",
    "debug",
    "function",
    "typescript",
    "javascript",
    "python",
    "java",
    "sql",
    "api",
    "코드",
    "버그",
    "프로그래밍",
    "함수",
}


def select_model(request: ChatCompletionRequest, settings: Settings) -> str:
    """Use an explicit model first; otherwise route code-related work to the coder model."""
    if request.model:
        return request.model

    prompt = " ".join(message.content.lower() for message in request.messages)
    if any(term in prompt for term in CODING_TERMS):
        return settings.coder_model
    return settings.default_model


def fallback_chain(primary_model: str, settings: Settings) -> list[str]:
    return list(dict.fromkeys([primary_model, settings.fallback_model]))
