
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


def _resolve_local_llm_model_path():
    configured_path = os.environ.get("LOCAL_LLM_MODEL_PATH")
    configured_file = os.environ.get("LOCAL_LLM_MODEL_FILE")
    candidate = configured_path or configured_file or DEFAULT_LOCAL_LLM_MODEL_FILE
    if os.path.isabs(candidate):
        return candidate
    return os.path.join(MODEL_DIR, candidate)


LLM_MODEL_PATH = _resolve_local_llm_model_path()

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

# Neural net confidence threshold (0.0 - 1.0) used to decide whether to use the
# neural net's answer or fall back to the LLM. Keep high if you prefer LLMs.
NEURAL_NET_CONFIDENCE_THRESHOLD = 0.8

# Conversation memory limits. Recent turns stay verbatim; older turns are
# compressed into a lightweight summary for LLM fallback context.
MEMORY_MAX_INTERACTIONS = int(os.environ.get("MEMORY_MAX_INTERACTIONS", "20"))
MEMORY_SUMMARY_MAX_CHARS = int(os.environ.get("MEMORY_SUMMARY_MAX_CHARS", "1200"))

# LLM generation timeout (seconds) — used by async or guarded calls.
LLM_MAX_GENERATION_TIME = 10

# Remote provider name (optional) — e.g., 'openai', 'openrouter', or None for local
LLM_API_PROVIDER = os.environ.get("LLM_API_PROVIDER") or None

# By default external providers are disabled. Set ENABLE_EXTERNAL_PROVIDER=true
# to allow using remote LLM providers (requires provider keys in env/secret store).
ENABLE_EXTERNAL_PROVIDER = _env_bool("ENABLE_EXTERNAL_PROVIDER", False)
LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME") or None

# Neural Net Hyperparameters (shared between training and inference)
NEURAL_NET_MAXLEN = 20
NEURAL_NET_VOCAB_SIZE = 1000
NEURAL_NET_EMBEDDING_DIM = 16

# External provider configuration (optional)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or ""
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or ""
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY") or ""
NVIDIA_BASE_URL = os.environ.get("NVIDIA_BASE_URL") or "https://api.nvidia.com"
PROVIDER_REQUEST_TIMEOUT = int(os.environ.get("PROVIDER_REQUEST_TIMEOUT", "15"))
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY") or ""
HUGGINGFACE_BASE_URL = os.environ.get("HUGGINGFACE_BASE_URL") or "https://api-inference.huggingface.co/models"
