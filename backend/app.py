import logging
import os
import threading
import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _sentiment_available = True
except Exception:
    SentimentIntensityAnalyzer = None
    _sentiment_available = False

from core.actions import Actions
from core.mock_engine import MockSpeechEngine
from ai.external_llm import ExternalLLM
from core.prompt_templates import clean_llm_response
import core.memory_store as memory_store

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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    await limiter(request)

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
RATE_LIMIT_COOLDOWN = 1.0

NEURAL_FAILURE_PHRASES = {
    "I'm afraid I didn't catch that, sir.",
    "Could you rephrase that directive?",
    "My processing units require clarification, sir.",
    "I'm not sure how to respond to that.",
}


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


@app.get("/metrics")
def metrics():
    if not _PROMETHEUS_AVAILABLE or generate_latest is None:
        return Response(content="Prometheus client unavailable\n", media_type="text/plain")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/command", response_model=CommandResponse, dependencies=[Depends(distributed_rate_limit)])
def process_command(request: CommandRequest):
    global LAST_COMMAND_TIME
    
    with _state_lock:
        current_time = time.time()
        if not request.confirm and current_time - LAST_COMMAND_TIME < RATE_LIMIT_COOLDOWN:
            return CommandResponse(
                response="Rate limit exceeded. Please wait.",
                action_status="ignored",
                sentiment="negative",
                metadata=ResponseMetadata(engine="rate_limiter", fallback_reason="cooldown_active"),
            )
        LAST_COMMAND_TIME = current_time

    query = (request.pending_command or request.command).lower()
    logger.info("Processing command: %s", query)
    
    mock_engine = MockSpeechEngine()
    actions = Actions(mock_engine)
    metadata = ResponseMetadata(engine="actions")
    
    def dummy_input():
        return "None"
    
    def dummy_exit():
        mock_engine.speak("Disconnecting...")

    try:
        needs_confirmation = bool(
            hasattr(actions, "_requires_confirmation") and actions._requires_confirmation(query)
        )
        if needs_confirmation and not request.confirm:
            return CommandResponse(
                response=(
                    "This action may delete data or change system settings. "
                    "Say yes to continue or no to cancel."
                ),
                action_status="confirmation_required",
                sentiment="neutral",
                pending_command=query,
                metadata=ResponseMetadata(
                    engine="actions",
                    fallback_reason="confirmation_required",
                ),
            )

        confirmation_input = (lambda: "yes") if request.confirm else dummy_input
        result = actions.process_command(query, input_func=confirmation_input, exit_func=dummy_exit)
        
        if result == "neural_net_fallback":
            response_text = None
            metadata = ResponseMetadata(engine="fallback", fallback_reason="actions_unhandled")
            
            if getattr(config, "USE_NEURAL_NET", True) and brain:
                try:
                    if hasattr(brain, 'predict_with_confidence'):
                        resp, conf = brain.predict_with_confidence(query)
                    else:
                        resp = brain.predict(query)
                        conf = 1.0 if resp else 0.0
                except Exception:
                    logger.exception("Error during neural net prediction")
                    resp, conf = None, 0.0

                metadata.confidence = round(conf, 4)
                threshold = getattr(config, 'NEURAL_NET_CONFIDENCE_THRESHOLD', 0.8)
                if resp and resp not in NEURAL_FAILURE_PHRASES and conf >= threshold:
                    response_text = resp
                    metadata.engine = "neural_net"
                    metadata.fallback_reason = None
                elif resp in NEURAL_FAILURE_PHRASES:
                    metadata.fallback_reason = "neural_net_noanswer"
                else:
                    metadata.fallback_reason = "neural_net_low_confidence"
            elif not getattr(config, "USE_NEURAL_NET", True):
                metadata.fallback_reason = "neural_net_disabled"
            else:
                metadata.fallback_reason = "neural_net_unavailable"

            if not response_text and getattr(config, "USE_LLM", True):
                summary = _memory_summary()
                if llm:
                    try:
                        response_text = llm.generate_response(
                            query,
                            history=CONVERSATION_HISTORY,
                            memory_summary=summary,
                        )
                        response_text = clean_llm_response(response_text)
                        if response_text:
                            metadata.engine = "local_llm"
                    except Exception:
                        logger.exception("Local LLM generation failed")
                        metadata.fallback_reason = "local_llm_error"
                else:
                    metadata.fallback_reason = "local_llm_unavailable"

                if not response_text and external_llm:
                    try:
                        response_text = external_llm.generate_response(
                            query,
                            history=CONVERSATION_HISTORY,
                            memory_summary=summary,
                        )
                        response_text = clean_llm_response(response_text)
                        if response_text:
                            metadata.engine = "external_llm"
                    except Exception:
                        logger.exception("External LLM generation failed")
                        metadata.fallback_reason = "external_llm_error"
                elif not response_text and external_llm is None:
                    metadata.fallback_reason = "external_llm_unavailable"
            elif not response_text:
                metadata.fallback_reason = "llm_disabled"

            if not response_text:
                response_text = "I am unable to process that request."
                metadata.engine = "none"
                metadata.fallback_reason = metadata.fallback_reason or "all_engines_failed"

            mock_engine.speak(response_text)
        
        final_response = mock_engine.get_response()
        
        if not final_response:
             final_response = "Done."

        with _state_lock:
            try:
                _append_conversation(query, final_response)
            except Exception:
                logger.exception("Failed to write conversation to memory store")

        sentiment = analyze_sentiment(final_response)

        return CommandResponse(
            response=final_response,
            action_status="success",
            sentiment=sentiment,
            pending_command=None,
            metadata=metadata,
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
    return {
        "status": "ok",
        "use_neural_net": getattr(config, "USE_NEURAL_NET", True),
        "neural_net_loaded": brain is not None,
        "use_llm": getattr(config, "USE_LLM", True),
        "llm_loaded": llm is not None,
        "external_llm_configured": bool(getattr(external_llm, "enabled", False)),
        "conversation_history_len": len(CONVERSATION_HISTORY),
        "memory_summary_chars": len(_memory_summary()),
    }


@app.get("/settings")
def get_settings():
    settings_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "data",
        "settings.json",
    )
    settings_path = os.path.abspath(settings_path)
    try:
        if not os.path.exists(settings_path):
            return {}
        import json
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Failed to read settings")
        raise HTTPException(status_code=500, detail="Failed to read settings")


@app.post("/settings")
def update_settings(payload: dict):
    settings_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "data",
        "settings.json",
    )
    settings_path = os.path.abspath(settings_path)
    try:
        import json
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return {"status": "ok"}
    except Exception:
        logger.exception("Failed to write settings")
        raise HTTPException(status_code=500, detail="Failed to write settings")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
