"""Optional, privacy-conscious MLflow tracing for the gateway."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

from app.config import Settings
from app.models import ChatCompletionRequest


class TraceRecorder:
    def __init__(self, settings: Settings):
        self._enabled = False
        self._mlflow: Optional[Any] = None
        self._settings = settings
        if not settings.mlflow_tracing_enabled:
            return

        try:
            import mlflow

            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            mlflow.set_experiment(settings.mlflow_experiment_name)
            self._mlflow = mlflow
            self._enabled = True
        except ImportError as exc:
            raise RuntimeError(
                "MLflow tracing is enabled, but mlflow-tracing is not installed. "
                "Use the Docker image or install the observability extra on Python 3.10+."
            ) from exc

    def _request_inputs(self, payload: ChatCompletionRequest, selected_model: str) -> dict:
        metadata = {
            "message_count": len(payload.messages),
            "roles": [message.role for message in payload.messages],
            "selected_model": selected_model,
        }
        if self._settings.trace_content_enabled:
            metadata["messages"] = [message.model_dump() for message in payload.messages]
        return metadata

    @contextmanager
    def request_span(
        self, payload: ChatCompletionRequest, selected_model: str
    ) -> Generator[Optional[Any], None, None]:
        if not self._enabled:
            yield None
            return

        with self._mlflow.start_span(name="ollama.chat", span_type="LLM") as span:
            span.set_inputs(self._request_inputs(payload, selected_model))
            yield span

    @staticmethod
    def success(span: Optional[Any], model: str, fallback_used: bool, latency_seconds: float) -> None:
        if span is not None:
            span.set_outputs(
                {
                    "served_model": model,
                    "fallback_used": fallback_used,
                    "latency_seconds": round(latency_seconds, 3),
                }
            )

    @staticmethod
    def failure(span: Optional[Any], error: str) -> None:
        if span is not None:
            span.set_attributes({"error": error})
