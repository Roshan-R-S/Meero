import logging
import os
import threading
import time
import base64
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _sentiment_available = True
except Exception:
    SentimentIntensityAnalyzer = None
    _sentiment_available = False

import core.memory_store as memory_store

from .command_service import execute_command
from .middleware import auth as auth_middleware
from .middleware import rate_limit as rate_limit_middleware
from .middleware.errors import global_exception_handler
from .voice import LocalVoicePipeline
from .voice.audio_utils import AudioValidationError
from .voice.schemas import SynthesisRequest, TranscriptionResponse, VoiceCommandResponse
from .voice.stt_service import STTUnavailableError
from .voice.tts_service import TTSUnavailableError

try:
    from ai.neural_net import NeuralNet
except Exception:
    NeuralNet = None

try:
    from ai.llm_engine import LLMEngine
except Exception:
    LLMEngine = None
import config

FastAPILimiter = rate_limit_middleware.FastAPILimiter
RateLimiter = rate_limit_middleware.RateLimiter

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
_RATE_LIMITER_READY = False

if _sentiment_available and SentimentIntensityAnalyzer is not None:
    _sentiment_analyzer = SentimentIntensityAnalyzer()
else:
    _sentiment_analyzer = None

from core.reminder_service import get_reminder_service

@asynccontextmanager
async def lifespan(_app: FastAPI):
    threading.Thread(target=_load_llm_background, daemon=True).start()
    reminder_srv = get_reminder_service()
    reminder_srv.start_daemon()
    await startup_rate_limiter()
    yield
    reminder_srv.stop_daemon()


app = FastAPI(title="Meero Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(Exception, global_exception_handler)

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


async def startup_rate_limiter():
    global _RATE_LIMITER_READY
    await rate_limit_middleware.initialize()
    _RATE_LIMITER_READY = rate_limit_middleware.ready


async def distributed_rate_limit(request: Request):
    rate_limit_middleware.ready = _RATE_LIMITER_READY
    rate_limit_middleware.FastAPILimiter = FastAPILimiter
    rate_limit_middleware.RateLimiter = RateLimiter
    await rate_limit_middleware.check(request)


if getattr(config, "USE_NEURAL_NET", True) and NeuralNet is not None:
    try:
        brain = NeuralNet()
        logger.info("NeuralNet initialized successfully.")
    except Exception as e:
        logger.error("Error loading NeuralNet: %s", e)
        brain = None
else:
    brain = None

llm = None
_llm_status = {
    "loading": False,
    "missing": False,
    "ready": False,
    "message": ""
}
voice_pipeline = LocalVoicePipeline()

def _load_llm_background():
    global llm, _llm_status
    if not getattr(config, "USE_LLM", True) or LLMEngine is None:
        _llm_status["message"] = "LLM disabled in config or not installed."
        return

    if not os.path.exists(MODEL_PATH):
        logger.warning(f"GGUF model file not found at {MODEL_PATH}")
        _llm_status["missing"] = True
        _llm_status["message"] = "Model file not found"
        return

    _llm_status["loading"] = True
    try:
        llm = LLMEngine(MODEL_PATH)
        logger.info("LLM initialized via GPT4All (Standalone).")
        _llm_status["ready"] = True
        _llm_status["loading"] = False
    except Exception as e:
        logger.error("Error loading GPT4All: %s", e)
        _llm_status["loading"] = False
        _llm_status["message"] = f"Error: {e}"



class CommandRequest(BaseModel):
    command: str
    mode: str = "voice"
    confirm: bool = False
    pending_command: Optional[str] = None


class ResponseMetadata(BaseModel):
    engine: str = "unknown"
    confidence: Optional[float] = None
    fallback_reason: Optional[str] = None
    intent: Optional[str] = None
    latency_ms: Optional[float] = None
    decision_trace: list[dict] = Field(default_factory=list)


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
    local_voice_enabled: Optional[bool] = None
    browser_speech_fallback_enabled: Optional[bool] = None


LOCAL_HOSTS = auth_middleware.LOCAL_HOSTS


def _client_host(request: Request) -> str:
    return auth_middleware.client_host(request)


def _is_local_request(request: Request) -> bool:
    return auth_middleware.is_local_request(request)


def require_local_request(request: Request) -> None:
    if not _is_local_request(request):
        raise HTTPException(status_code=403, detail="This endpoint is available only locally")


def require_api_key(x_meero_api_key: Optional[str] = Header(default=None)) -> None:
    auth_middleware.require_api_key(x_meero_api_key)


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

    try:
        logger.info("Processing command mode=%s", payload.mode)

        outcome = execute_command(
            payload.command,
            mode=payload.mode,
            confirm=payload.confirm,
            pending_command=payload.pending_command,
            brain=brain,
            llm=llm,
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


@app.get("/memory", dependencies=[Depends(require_local_request), Depends(require_api_key)])
def export_memory():
    """Export the local SQLite memory for the user."""
    return memory_store.export()


@app.delete("/memory", dependencies=[Depends(require_local_request), Depends(require_api_key)])
def clear_memory():
    """Clear the local SQLite memory."""
    memory_store.clear()
    global CONVERSATION_HISTORY
    with _state_lock:
        CONVERSATION_HISTORY = []
    return {"status": "memory_cleared"}


def _voice_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AudioValidationError) or isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, (STTUnavailableError, TTSUnavailableError)):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Local voice processing failed")


@app.post(
    "/voice/transcribe",
    response_model=TranscriptionResponse,
    dependencies=[Depends(require_local_request), Depends(require_api_key)],
)
async def transcribe_voice(audio: UploadFile = File(...)):
    try:
        transcript = voice_pipeline.transcribe(await audio.read())
        return TranscriptionResponse(transcript=transcript, provider=voice_pipeline.stt.provider)
    except Exception as exc:
        raise _voice_http_error(exc) from exc


@app.post(
    "/voice/synthesize",
    dependencies=[Depends(require_local_request), Depends(require_api_key)],
)
def synthesize_voice(payload: SynthesisRequest):
    try:
        return Response(content=voice_pipeline.synthesize(payload.text), media_type="audio/wav")
    except Exception as exc:
        raise _voice_http_error(exc) from exc


@app.post(
    "/voice-command",
    response_model=VoiceCommandResponse,
    dependencies=[
        Depends(distributed_rate_limit),
        Depends(require_local_request),
        Depends(require_api_key),
    ],
)
async def process_voice_command(
    http_request: Request,
    audio: UploadFile = File(...),
    confirm: bool = Form(False),
    pending_command: Optional[str] = Form(None),
    synthesize: bool = Form(True),
):
    try:
        result = voice_pipeline.execute(
            await audio.read(),
            execute_command,
            synthesize=synthesize,
            confirm=confirm,
            pending_command=pending_command,
            brain=brain,
            llm=llm,
            conversation_history=CONVERSATION_HISTORY,
            memory_summary_fn=_memory_summary,
            append_conversation_fn=_append_conversation,
            analyze_sentiment_fn=analyze_sentiment,
            client_is_local=_is_local_request(http_request),
        )
        audio_base64 = base64.b64encode(result.audio).decode("ascii") if result.audio else None
        return VoiceCommandResponse(
            transcript=result.transcript,
            response=result.outcome.response,
            action_status=result.outcome.action_status,
            sentiment=result.outcome.sentiment,
            pending_command=result.outcome.pending_command,
            metadata=result.outcome.metadata,
            audio_base64=audio_base64,
            audio_mime_type="audio/wav" if audio_base64 else None,
        )
    except Exception as exc:
        raise _voice_http_error(exc) from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model/status", dependencies=[Depends(require_local_request), Depends(require_api_key)])
def model_status():
    """Return the status of the local models for UI lazy-loading and management."""
    status_str = "ready" if _llm_status["ready"] else ("missing" if _llm_status["missing"] else ("loading" if _llm_status["loading"] else "error"))
    return {
        "neural_net": {
            "enabled": getattr(config, "USE_NEURAL_NET", True),
            "loaded": brain is not None,
            "name": os.path.basename(getattr(config, "NEURAL_NET_MODEL_PATH", "models/chat_model.h5"))
        },
        "gguf_llm": {
            "enabled": getattr(config, "USE_LLM", True),
            "loaded": _llm_status["ready"],
            "status": status_str,
            "message": _llm_status["message"],
            "name": os.path.basename(MODEL_PATH)
        },
        "voice": voice_pipeline.status(),
    }


def _debug_health():
    return {
        "status": "ok",
        "use_neural_net": getattr(config, "USE_NEURAL_NET", True),
        "neural_net_loaded": brain is not None,
        "use_llm": getattr(config, "USE_LLM", True),
        "llm_loaded": llm is not None,

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
