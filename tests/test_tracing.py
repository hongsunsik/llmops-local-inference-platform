from app.config import Settings
from app.models import ChatCompletionRequest, ChatMessage
from app.tracing import TraceRecorder


def test_trace_content_is_redacted_by_default() -> None:
    settings = Settings(trace_content_enabled=False)
    recorder = TraceRecorder(settings)
    request = ChatCompletionRequest(messages=[ChatMessage(role="user", content="private prompt")])

    trace_input = recorder._request_inputs(request, "qwen3:8b")

    assert trace_input["message_count"] == 1
    assert "messages" not in trace_input


def test_trace_content_can_be_explicitly_enabled() -> None:
    settings = Settings(trace_content_enabled=True)
    recorder = TraceRecorder(settings)
    request = ChatCompletionRequest(messages=[ChatMessage(role="user", content="trace this prompt")])

    assert recorder._request_inputs(request, "qwen3:8b")["messages"][0]["content"] == "trace this prompt"
