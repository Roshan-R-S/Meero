import sys
import time
import logging
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

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
import os
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = config.LLM_MODEL_PATH

# Global State (single-user local app; protected by lock for safety)
_state_lock = threading.Lock()
CONVERSATION_HISTORY = []

# Sentiment Analyzer (VADER — rule-based, no training needed)
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
    
    # External LLM (API-based) — optional and lightweight
    try:
        external_llm = ExternalLLM()
    except Exception:
        external_llm = None

class CommandRequest(BaseModel):
    command: str
    mode: str = "voice" # 'voice' or 'text' from frontend perspective

class CommandResponse(BaseModel):
    response: str
    action_status: str
    sentiment: str = "neutral"

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

@app.get("/")
def read_root():
    return {"status": "Meero is online"}

@app.post("/command", response_model=CommandResponse)
def process_command(request: CommandRequest):
    global LAST_COMMAND_TIME
    
    with _state_lock:
        current_time = time.time()
        if current_time - LAST_COMMAND_TIME < RATE_LIMIT_COOLDOWN:
            return CommandResponse(
                response="Rate limit exceeded. Please wait.",
                action_status="ignored",
                sentiment="negative"
            )
        LAST_COMMAND_TIME = current_time

    query = request.command.lower()
    logger.info("Processing command: %s", query)
    
    # Setup Mock Engine for this request to capture output
    mock_engine = MockSpeechEngine()
    actions = Actions(mock_engine)
    
    # Dummy input function for now (skips interactive questions)
    def dummy_input():
        return "None"
    
    # Dummy exit function
    def dummy_exit():
        mock_engine.speak("Disconnecting...")

    try:
        # 1. Try Actions
        result = actions.process_command(query, input_func=dummy_input, exit_func=dummy_exit)
        
        # 2. If Actions didn't handle it, use Neural Net + LLM Hybrid
        if result == "neural_net_fallback":
            response_text = None
            
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

                # Check if brain gave a "failure" response (from noanswer tag)
                failure_phrases = [
                    "I'm afraid I didn't catch that, sir.",
                    "Could you rephrase that directive?",
                    "My processing units require clarification, sir.",
                    "I'm not sure how to respond to that."
                ]

                if resp and resp not in failure_phrases and conf >= getattr(config, 'NEURAL_NET_CONFIDENCE_THRESHOLD', 0.8):
                    response_text = resp

            # Step B: If Brain failed, prefer local LLM then external LLM if enabled
            if not response_text and getattr(config, "USE_LLM", True):
                if llm:
                    try:
                        response_text = llm.generate_response(query, history=CONVERSATION_HISTORY)
                    except Exception:
                        logger.exception("Local LLM generation failed")

                # Try external API-based LLM if local LLM didn't produce an answer
                if not response_text and external_llm:
                    try:
                        response_text = external_llm.generate_response(query, history=CONVERSATION_HISTORY)
                    except Exception:
                        logger.exception("External LLM generation failed")

            if not response_text:
                response_text = "I am unable to process that request."

            mock_engine.speak(response_text)
        
        # 3. Retrieve captured text
        final_response = mock_engine.get_response()
        
        if not final_response:
             final_response = "Done." # Fallback if action happened but no speech

        # Update History (in-memory and persistent)
        with _state_lock:
            CONVERSATION_HISTORY.append((query, final_response))
            # Keep only last 20 interactions
            if len(CONVERSATION_HISTORY) > 20:
                CONVERSATION_HISTORY.pop(0)
            try:
                memory_store.append(query, final_response)
            except Exception:
                logger.exception("Failed to write conversation to memory store")

        # Calculate Sentiment (VADER)
        sentiment = analyze_sentiment(final_response)

        return CommandResponse(
            response=final_response,
            action_status="success",
            sentiment=sentiment
        )
        
    except Exception as e:
        logger.exception("Error processing command")
        return CommandResponse(
            response="I encountered an internal error. Please try again.",
            action_status="error",
            sentiment="negative"
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
        "conversation_history_len": len(CONVERSATION_HISTORY)
    }


@app.get("/settings")
def get_settings():
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json")
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
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json")
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
