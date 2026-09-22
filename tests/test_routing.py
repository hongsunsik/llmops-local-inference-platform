from app.config import Settings
from app.models import ChatCompletionRequest, ChatMessage
from app.routing import fallback_chain, select_model


def test_code_prompt_routes_to_coder_model() -> None:
    settings = Settings()
    request = ChatCompletionRequest(messages=[ChatMessage(role="user", content="Fix this Python bug")])

    assert select_model(request, settings) == settings.coder_model


def test_explicit_model_overrides_router() -> None:
    settings = Settings()
    request = ChatCompletionRequest(
        model="custom-model", messages=[ChatMessage(role="user", content="Write code")]
    )

    assert select_model(request, settings) == "custom-model"


def test_fallback_chain_deduplicates_primary() -> None:
    settings = Settings(default_model="model-a", fallback_model="model-a")

    assert fallback_chain("model-a", settings) == ["model-a"]
