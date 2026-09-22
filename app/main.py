import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import Settings, get_settings
from app.models import ChatCompletionRequest, ChatCompletionResponse
from app.routing import fallback_chain, select_model
from app.tracing import TraceRecorder

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REQUESTS = Counter(
    "llm_gateway_requests_total", "Requests handled by the gateway", ["model", "outcome"]
)
LATENCY = Histogram("llm_gateway_request_duration_seconds", "Gateway request latency", ["model"])
FALLBACKS = Counter("llm_gateway_fallbacks_total", "Fallbacks used by the gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.client = httpx.AsyncClient(
        base_url=settings.ollama_base_url.rstrip("/"),
        timeout=httpx.Timeout(settings.request_timeout_seconds),
    )
    app.state.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    app.state.tracer = TraceRecorder(settings)
    yield
    await app.state.client.aclose()


app = FastAPI(title="Local LLMOps Gateway", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    try:
        response = await request.app.state.client.get("/api/tags")
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Ollama is unavailable") from exc
    models = [model["name"] for model in response.json().get("models", [])]
    return {"status": "ok", "track": settings.gateway_track, "ollama_models": models}


@app.middleware("http")
async def add_track_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Gateway-Track"] = request.app.state.settings.gateway_track
    return response


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(payload: ChatCompletionRequest, request: Request) -> ChatCompletionResponse:
    if payload.stream:
        raise HTTPException(status_code=400, detail="Streaming is not implemented in this MVP")

    settings: Settings = request.app.state.settings
    primary_model = select_model(payload, settings)
    trace_id = str(uuid.uuid4())
    started = time.perf_counter()

    tracer: TraceRecorder = request.app.state.tracer
    with tracer.request_span(payload, primary_model) as span:
        async with request.app.state.semaphore:
            for attempt, model in enumerate(fallback_chain(primary_model, settings)):
                try:
                    upstream = await request.app.state.client.post(
                        "/api/chat",
                        json={
                            "model": model,
                            "messages": [message.model_dump() for message in payload.messages],
                            "stream": False,
                            "options": {"temperature": payload.temperature},
                        },
                    )
                    upstream.raise_for_status()
                    result = upstream.json()
                    fallback_used = attempt > 0
                    if fallback_used:
                        FALLBACKS.inc()
                    latency_seconds = time.perf_counter() - started
                    REQUESTS.labels(model=model, outcome="success").inc()
                    LATENCY.labels(model=model).observe(latency_seconds)
                    tracer.success(span, model, fallback_used, latency_seconds)
                    logger.info(
                        "trace_id=%s model=%s fallback_used=%s latency_seconds=%.3f",
                        trace_id,
                        model,
                        fallback_used,
                        latency_seconds,
                    )
                    return ChatCompletionResponse(
                        id=trace_id,
                        model=model,
                        fallback_used=fallback_used,
                        choices=[
                            {
                                "index": 0,
                                "message": result["message"],
                                "finish_reason": "stop",
                            }
                        ],
                        usage={
                            "prompt_tokens": result.get("prompt_eval_count"),
                            "completion_tokens": result.get("eval_count"),
                        },
                    )
                except httpx.HTTPError as exc:
                    logger.warning("trace_id=%s model=%s upstream_error=%s", trace_id, model, exc)

        tracer.failure(span, "all configured local models are unavailable")
        REQUESTS.labels(model=primary_model, outcome="failure").inc()
        LATENCY.labels(model=primary_model).observe(time.perf_counter() - started)
    raise HTTPException(status_code=503, detail="All configured local models are unavailable")
