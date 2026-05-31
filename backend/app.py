import logging
import os
import threading
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _sentiment_available = True
except Exception:
    SentimentIntensityAnalyzer = None
    _sentiment_available = False

import core.memory_store as memory_store
from ai.external_llm import ExternalLLM
from .command_service import execute_command

try:
    from ai.neural_net import NeuralNet
except Exception:
    NeuralNet = None

try:
    from ai.llm_engine import LLMEngine
except Exception:
    LLMEngine = None
import config

try:
    from fastapi_limiter import FastAPILimiter
    from fastapi_limiter.depends import RateLimiter
    import redis.asyncio as redis
    _RATE_LIMITER_AVAILABLE = True
except Exception:
    FastAPILimiter = None
    RateLimiter = None
    redis = None
    _RATE_LIMITER_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest
    _PROMETHEUS_AVAILABLE = True
except Exception:
    Counter = None
    Histogram = None
    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"
    generate_latest = None
    _PROMETHEUS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = config.LLM_MODEL_PATH
_state_lock = threading.Lock()
CONVERSATION_HISTORY = []

if _sentiment_available and SentimentIntensityAnalyzer is not None:
    _sentiment_analyzer = SentimentIntensityAnalyzer()
else:
    _sentiment_analyzer = None

app = FastAPI(title="Meero Backend")

app.add_middleware(
    CORSMiddleware,
    # During local development allow the frontend origin. Use '*' to avoid
    # CORS issues when developing locally. In production set `CORS_ORIGINS`
    # appropriately in environment.
    allow_origins=getattr(config, "CORS_ORIGINS", ["http://localhost:5173"]) or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Log full exception server-side and return a JSON error so the frontend
    # can surface a helpful message instead of a silent 500.
    logger.exception("Unhandled exception during request: %s %s", request.method, request.url)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(exc)})

if _PROMETHEUS_AVAILABLE:
    HTTP_REQUESTS_TOTAL = Counter(
        "meero_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    HTTP_REQUEST_DURATION = Histogram(
        "meero_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
    )


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    if not _PROMETHEUS_AVAILABLE or request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        if _PROMETHEUS_AVAILABLE:
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                path=request.url.path,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                path=request.url.path,
            ).observe(elapsed)


@app.on_event("startup")
async def startup_rate_limiter():
    if not _RATE_LIMITER_AVAILABLE:
        logger.info("Rate limiter libraries not available; skipping init")
        return

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_client)
        logger.info("Rate limiter initialized with Redis: %s", redis_url)
    except Exception:
        logger.exception("Failed to initialize rate limiter; continuing without distributed limits")


async def distributed_rate_limit(request: Request):
    if RateLimiter is None or FastAPILimiter is None:
        return
    if not getattr(FastAPILimiter, "redis", None):
        return
    limiter = RateLimiter(times=10, seconds=60)
    try:
        await limiter(request)
    except Exception:
        # If the rate limiter (Redis) is unavailable or errors, log and
        # allow the request to proceed rather than raising a 500.
        logger.exception("Rate limiter check failed; continuing without applying distributed limits")
        return

external_llm = None
if getattr(config, "USE_NEURAL_NET", True) and NeuralNet is not None:
    try:
        brain = NeuralNet()
        logger.info("NeuralNet initialized successfully.")
    except Exception as e:
        logger.error("Error loading NeuralNet: %s", e)
        brain = None
else:
    brain = None

if getattr(config, "USE_LLM", True) and LLMEngine is not None:
    try:
        llm = LLMEngine(MODEL_PATH)
        logger.info("LLM initialized via GPT4All (Standalone).")
    except Exception as e:
        logger.error("Error loading GPT4All: %s", e)
        llm = None
else:
    llm = None
    
try:
    external_llm = ExternalLLM()
except Exception:
    external_llm = None


class CommandRequest(BaseModel):
    command: str
    mode: str = "voice"
    confirm: bool = False
    pending_command: Optional[str] = None


class ResponseMetadata(BaseModel):
    engine: str = "unknown"
    confidence: Optional[float] = None
    fallback_reason: Optional[str] = None


class CommandResponse(BaseModel):
    response: str
    action_status: str
    sentiment: str = "neutral"
    pending_command: Optional[str] = None
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)


class SettingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wake_word_enabled: Optional[bool] = None
    voice_rate: Optional[float] = Field(default=None, ge=0.5, le=2.0)
    voice_pitch: Optional[float] = Field(default=None, ge=0.5, le=2.0)
    mic_enabled: Optional[bool] = None
    text_output_enabled: Optional[bool] = None
    show_history: Optional[bool] = None
    text_input_enabled: Optional[bool] = None


LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def _client_host(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


def _is_local_request(request: Request) -> bool:
    host = _client_host(request)
    return host in LOCAL_HOSTS or host.startswith("127.")


def require_local_request(request: Request) -> None:
    if not _is_local_request(request):
        raise HTTPException(status_code=403, detail="This endpoint is available only locally")


def require_api_key(x_meero_api_key: Optional[str] = Header(default=None)) -> None:
    configured_key = getattr(config, "MEERO_API_KEY", "") or os.environ.get("MEERO_API_KEY", "")
    require_key = getattr(config, "REQUIRE_API_KEY", False)
    if require_key and not configured_key:
        raise HTTPException(status_code=500, detail="API key is required but not configured")
    if not configured_key:
        return
    if x_meero_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def require_metrics_access(x_meero_api_key: Optional[str] = Header(default=None)) -> None:
    if not getattr(config, "PROTECT_METRICS", False):
        return
    require_api_key(x_meero_api_key)


def analyze_sentiment(text: str) -> str:
    if _sentiment_analyzer is None:
        return "neutral"

    scores = _sentiment_analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    return "neutral"


LAST_COMMAND_TIME = 0
CLIENT_COMMAND_TIMES = {}
RATE_LIMIT_COOLDOWN = getattr(config, "RATE_LIMIT_COOLDOWN", 1.0)


def summarize_conversation(turns, existing_summary=""):
    return memory_store.summarize_turns(
        turns,
        existing_summary=existing_summary,
        max_chars=getattr(config, "MEMORY_SUMMARY_MAX_CHARS", 1200),
    )


def _append_conversation(query: str, response: str) -> None:
    max_interactions = getattr(config, "MEMORY_MAX_INTERACTIONS", 20)
    CONVERSATION_HISTORY.append((query, response))
    while len(CONVERSATION_HISTORY) > max_interactions:
        CONVERSATION_HISTORY.pop(0)
    memory_store.append(
        query,
        response,
        max_interactions=max_interactions,
        summarizer=summarize_conversation,
    )


def _memory_summary() -> str:
    try:
        return memory_store.get_summary()
    except Exception:
        logger.exception("Failed to read conversation summary")
        return ""


@app.get("/")
def read_root():
    return {"status": "Meero is online"}


@app.get("/metrics", dependencies=[Depends(require_metrics_access)])
def metrics():
    if not _PROMETHEUS_AVAILABLE or generate_latest is None:
        return Response(content="Prometheus client unavailable\n", media_type="text/plain")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/command",
    response_model=CommandResponse,
    dependencies=[Depends(distributed_rate_limit), Depends(require_api_key)],
)
def process_command(payload: CommandRequest, http_request: Request):
    global LAST_COMMAND_TIME
    
    with _state_lock:
        current_time = time.time()
        client_key = _client_host(http_request)
        last_command_time = CLIENT_COMMAND_TIMES.get(client_key, 0)
        if not payload.confirm and current_time - last_command_time < RATE_LIMIT_COOLDOWN:
            return CommandResponse(
                response="Rate limit exceeded. Please wait.",
                action_status="rate_limited",
                sentiment="negative",
                metadata=ResponseMetadata(engine="rate_limiter", fallback_reason="cooldown_active"),
            )
        CLIENT_COMMAND_TIMES[client_key] = current_time
        LAST_COMMAND_TIME = current_time

    try:
        raw_query = (payload.pending_command or payload.command).strip()
        logger.info("Processing command: %s", raw_query)

        outcome = execute_command(
            payload.command,
            confirm=payload.confirm,
            pending_command=payload.pending_command,
            brain=brain,
            llm=llm,
            external_llm=external_llm,
            conversation_history=CONVERSATION_HISTORY,
            memory_summary_fn=_memory_summary,
            append_conversation_fn=_append_conversation,
            analyze_sentiment_fn=analyze_sentiment,
            client_is_local=_is_local_request(http_request),
        )

        return CommandResponse(
            response=outcome.response,
            action_status=outcome.action_status,
            sentiment=outcome.sentiment,
            pending_command=outcome.pending_command,
            metadata=ResponseMetadata(**outcome.metadata),
        )
        
    except Exception as e:
        logger.exception("Error processing command")
        return CommandResponse(
            response="I encountered an internal error. Please try again.",
            action_status="error",
            sentiment="negative",
            metadata=ResponseMetadata(engine="error", fallback_reason=type(e).__name__),
        )


@app.get("/health")
def health():
    return {"status": "ok"}


def _debug_health():
    return {
        "status": "ok",
        "use_neural_net": getattr(config, "USE_NEURAL_NET", True),
        "neural_net_loaded": brain is not None,
        "use_llm": getattr(config, "USE_LLM", True),
        "llm_loaded": llm is not None,
        "external_llm_configured": bool(getattr(external_llm, "enabled", False)),
        "local_desktop_mode": getattr(config, "LOCAL_DESKTOP_MODE", False),
        "web_safe_mode": getattr(config, "WEB_SAFE_MODE", True),
        "conversation_history_len": len(CONVERSATION_HISTORY),
        "memory_summary_chars": len(_memory_summary()),
    }


@app.get("/debug/health", dependencies=[Depends(require_api_key)])
def debug_health():
    return _debug_health()


def _settings_path() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "data",
        "settings.json",
    ))


@app.get("/settings", dependencies=[Depends(require_local_request), Depends(require_api_key)])
def get_settings():
    settings_path = _settings_path()
    try:
        if not os.path.exists(settings_path):
            return {}
        import json
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Failed to read settings")
        raise HTTPException(status_code=500, detail="Failed to read settings")


@app.post("/settings", dependencies=[Depends(require_local_request), Depends(require_api_key)])
def update_settings(payload: SettingsPayload):
    settings_path = _settings_path()
    tmp_path = f"{settings_path}.tmp"
    try:
        import json
        data = payload.model_dump(exclude_none=True)
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, settings_path)
        return {"status": "ok"}
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            logger.exception("Failed to clean up temporary settings file")
        logger.exception("Failed to write settings")
        raise HTTPException(status_code=500, detail="Failed to write settings")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
