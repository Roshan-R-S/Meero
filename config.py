
import os
import json
import shutil


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ORIGINAL_ENV_KEYS = set(os.environ)


def _load_env_file(path, override_loaded=False):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if not key:
                continue
            # If the key existed in the original process environment, only
            # skip it when not explicitly allowing overrides. When
            # `override_loaded` is True (used for backend/.env) we should
            # allow replacing previously loaded values.
            if key in _ORIGINAL_ENV_KEYS and not override_loaded:
                continue
            if override_loaded or key not in os.environ:
                os.environ[key] = value


_load_env_file(os.path.join(BASE_DIR, ".env"))
_load_env_file(os.path.join(BASE_DIR, "backend", ".env"), override_loaded=True)


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name, default):
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]

# Assistant Settings
ASSISTANT_NAME = "Meero"
USER_NAME = "Roshan"

# Paths
INTENTS_FILE = os.path.join(BASE_DIR, "intents.json")
# Default model locations live under the `models/` directory. The training
# script will write versioned artifacts and also update the canonical
# filenames below so the app always loads the latest model by default.
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_FILE = os.path.join(MODEL_DIR, "chat_model.h5")
TOKENIZER_FILE = os.path.join(MODEL_DIR, "tokenizer.pkl")
LABEL_ENCODER_FILE = os.path.join(MODEL_DIR, "label_encoder.pkl")


# Apps (Adjust paths as needed)
CALCULATOR_PATH = 'C:\\Windows\\System32\\calc.exe'
NOTEPAD_PATH = 'C:\\Windows\\System32\\notepad.exe'
PAINT_PATH = 'C:\\Windows\\System32\\mspaint.exe'
VSCODE_PATH = shutil.which('code') or 'C:\\Windows\\System32\\code.exe'  # Auto-detect from PATH

# Social Media URLs
SOCIAL_MEDIA_URLS = {
    "facebook": "https://www.facebook.com/",
    "whatsapp": "https://web.whatsapp.com/",
    "discord": "https://discord.com/",
    "instagram": "https://www.instagram.com/",
    "youtube": "https://www.youtube.com/"
}

# University Schedule (loaded from data/schedule.json)
_schedule_path = os.path.join(BASE_DIR, "data", "schedule.json")
try:
    with open(_schedule_path, "r") as _f:
        SCHEDULE = json.load(_f)
except FileNotFoundError:
    SCHEDULE = {}

# LLM Configuration
DEFAULT_LOCAL_LLM_MODEL_FILE = "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
DEFAULT_GGUF_TEACHER_MODEL_FILES = [
    "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
    "mistral-7b-instruct-v0.1.Q5_K_M.gguf",
    "Qwen3-4B-Q2_K_L.gguf",
]


def _resolve_local_llm_model_path():
    configured_path = os.environ.get("LOCAL_LLM_MODEL_PATH")
    configured_file = os.environ.get("LOCAL_LLM_MODEL_FILE")
    candidate = configured_path or configured_file or DEFAULT_LOCAL_LLM_MODEL_FILE
    if os.path.isabs(candidate):
        return candidate
    return os.path.join(MODEL_DIR, candidate)


LLM_MODEL_PATH = _resolve_local_llm_model_path()


def _resolve_teacher_model_paths():
    resolved = []
    for candidate in DEFAULT_GGUF_TEACHER_MODEL_FILES:
        candidate_path = candidate if os.path.isabs(candidate) else os.path.join(MODEL_DIR, candidate)
        if os.path.exists(candidate_path):
            resolved.append(candidate_path)
    return resolved


DEFAULT_GGUF_TEACHER_MODEL_PATHS = _resolve_teacher_model_paths()

# Feature flags
# Set to False to disable loading/using the neural net or local LLM fallback
USE_NEURAL_NET = True
USE_LLM = True
LOCAL_DESKTOP_MODE = _env_bool("LOCAL_DESKTOP_MODE", False)
WEB_SAFE_MODE = _env_bool("WEB_SAFE_MODE", True)
CORS_ORIGINS = _env_list("CORS_ORIGINS", ["http://localhost:5173"])
RATE_LIMIT_COOLDOWN = float(os.environ.get("RATE_LIMIT_COOLDOWN", "1.0"))
MEERO_API_KEY = os.environ.get("MEERO_API_KEY", "")
REQUIRE_API_KEY = _env_bool("REQUIRE_API_KEY", False)
PROTECT_METRICS = _env_bool("PROTECT_METRICS", False)
APP_LAUNCH_ALLOWLIST = tuple(_env_list("APP_LAUNCH_ALLOWLIST", []))
APP_CLOSE_ALLOWLIST = tuple(_env_list("APP_CLOSE_ALLOWLIST", []))
APP_FORCE_CLOSE_ALLOWLIST = tuple(_env_list("APP_FORCE_CLOSE_ALLOWLIST", []))

# Neural net confidence threshold (0.0 - 1.0) used to decide whether to use the
# neural net's answer or fall back to the LLM. Keep high if you prefer LLMs.
NEURAL_NET_CONFIDENCE_THRESHOLD = 0.8

# Conversation memory limits. Recent turns stay verbatim; older turns are
# compressed into a lightweight summary for LLM fallback context.
MEMORY_MAX_INTERACTIONS = int(os.environ.get("MEMORY_MAX_INTERACTIONS", "20"))
MEMORY_SUMMARY_MAX_CHARS = int(os.environ.get("MEMORY_SUMMARY_MAX_CHARS", "1200"))

# Neural Net Hyperparameters (shared between training and inference)
NEURAL_NET_MAXLEN = 20
NEURAL_NET_VOCAB_SIZE = 1000
NEURAL_NET_EMBEDDING_DIM = 16

# LLM generation timeout (seconds) — used by async or guarded calls.
LLM_MAX_GENERATION_TIME = 10

# Debug flag — when True, unhandled exception responses include the error
# detail string.  Keep False in production to avoid leaking internals.
DEBUG_ERRORS = _env_bool("DEBUG_ERRORS", False)

# Rate-limiter resilience — when True (default), a Redis/rate-limiter failure
# allows the request through.  Set to False in production to fail closed.
RATE_LIMIT_FAIL_OPEN = _env_bool("RATE_LIMIT_FAIL_OPEN", True)

