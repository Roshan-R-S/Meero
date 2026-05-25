import logging
import os
import sys
import threading
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Some optional heavy modules (ML, sentiment) are imported lazily
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _sentiment_available = True
except Exception:
    SentimentIntensityAnalyzer = None
    _sentiment_available = False

from actions import Actions
from mock_engine import MockSpeechEngine
from external_llm import ExternalLLM
import memory_store

# neural_net and llm_engine may require large native deps; import safely
try:
    from neural_net import NeuralNet
except Exception:
    NeuralNet = None

try:
    from llm_engine import LLMEngine
except Exception:
    LLMEngine = None
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = config.LLM_MODEL_PATH

# Global State (single-user local app; protected by lock for safety)
_state_lock = threading.Lock()
CONVERSATION_HISTORY = []

# Sentiment Analyzer (VADER rule-based, no training needed)
if _sentiment_available and SentimentIntensityAnalyzer is not None:
    _sentiment_analyzer = SentimentIntensityAnalyzer()
else:
    _sentiment_analyzer = None


app = FastAPI(title="Meero Backend")

# Security Protocols: Origin Locking
# Only allow the local frontend to communicate with the Brain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Locked to local frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Components (safe: heavy modules may be None)
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
    mode: str = "voice" # 'voice' or 'text' from frontend perspective
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
    """Use VADER to classify sentiment as positive/negative/neutral."""
    if _sentiment_analyzer is None:
        return "neutral"

    scores = _sentiment_analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    return "neutral"

# Circuit Breaker: Rate Limiting
LAST_COMMAND_TIME = 0
RATE_LIMIT_COOLDOWN = 1.0  # Seconds between commands

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

@app.post("/command", response_model=CommandResponse)
def process_command(request: CommandRequest):
    global LAST_COMMAND_TIME
    
    with _state_lock:
        current_time = time.time()
        # Allow immediate follow-up for confirmations.
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
    
    # Setup Mock Engine for this request to capture output
    mock_engine = MockSpeechEngine()
    actions = Actions(mock_engine)
    metadata = ResponseMetadata(engine="actions")
    
    # Dummy input function for now (skips interactive questions)
    def dummy_input():
        return "None"
    
    # Dummy exit function
    def dummy_exit():
        mock_engine.speak("Disconnecting...")

    try:
        # Two-step confirmation path for sensitive commands in API mode.
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

        # 1. Try Actions
        result = actions.process_command(query, input_func=confirmation_input, exit_func=dummy_exit)
        
        # 2. If Actions didn't handle it, use Neural Net + LLM Hybrid
        if result == "neural_net_fallback":
            response_text = None
            metadata = ResponseMetadata(engine="fallback", fallback_reason="actions_unhandled")
            
            # Step A: Try Neural Net (Fast, generic intents) if enabled
            if getattr(config, "USE_NEURAL_NET", True) and brain:
                # Use the predict_with_confidence interface when available
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

            # Step B: If Brain failed, prefer local LLM then external LLM if enabled
            if not response_text and getattr(config, "USE_LLM", True):
                summary = _memory_summary()
                if llm:
                    try:
                        response_text = llm.generate_response(
                            query,
                            history=CONVERSATION_HISTORY,
                            memory_summary=summary,
                        )
                        if response_text:
                            metadata.engine = "local_llm"
                    except Exception:
                        logger.exception("Local LLM generation failed")
                        metadata.fallback_reason = "local_llm_error"
                else:
                    metadata.fallback_reason = "local_llm_unavailable"

                # Try external API-based LLM if local LLM didn't produce an answer
                if not response_text and external_llm:
                    try:
                        response_text = external_llm.generate_response(
                            query,
                            history=CONVERSATION_HISTORY,
                            memory_summary=summary,
                        )
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
        
        # 3. Retrieve captured text
        final_response = mock_engine.get_response()
        
        if not final_response:
             final_response = "Done." # Fallback if action happened but no speech

        # Update History (in-memory and persistent)
        with _state_lock:
            try:
                _append_conversation(query, final_response)
            except Exception:
                logger.exception("Failed to write conversation to memory store")

        # Calculate Sentiment (VADER)
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
    """Return simple health and feature-flag status for the service."""
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
        "data",
        "settings.json",
    )
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
        "data",
        "settings.json",
    )
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
