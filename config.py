
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
DATA_DIR = os.path.join(BASE_DIR, "data")
INTENTS_FILE = os.path.join(DATA_DIR, "intents.json")
# Default model locations live under the `models/` directory. The training
# script will write versioned artifacts and also update the canonical
# filenames below so the app always loads the latest model by default.
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)
LOCAL_LLM_DIR = os.path.join(MODEL_DIR, "local-llm")
LOCAL_STT_DIR = os.path.join(MODEL_DIR, "local-stt")
LOCAL_TTS_DIR = os.path.join(MODEL_DIR, "local-tts")
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
    preferred = os.path.join(LOCAL_LLM_DIR, candidate)
    legacy = os.path.join(MODEL_DIR, candidate)
    return preferred if os.path.exists(preferred) or not os.path.exists(legacy) else legacy


LLM_MODEL_PATH = _resolve_local_llm_model_path()


def _resolve_teacher_model_paths():
    resolved = []
    for candidate in DEFAULT_GGUF_TEACHER_MODEL_FILES:
        if os.path.isabs(candidate):
            candidates = [candidate]
        else:
            candidates = [
                os.path.join(LOCAL_LLM_DIR, candidate),
                os.path.join(MODEL_DIR, candidate),
            ]
        existing = next((path for path in candidates if os.path.exists(path)), None)
        if existing:
            resolved.append(existing)
    return resolved


DEFAULT_GGUF_TEACHER_MODEL_PATHS = _resolve_teacher_model_paths()

# Feature flags
# Set to False to disable loading/using the neural net or local LLM fallback
USE_NEURAL_NET = True
USE_LLM = True


def _default_llm_device() -> str:
    explicit = os.environ.get("LLM_DEVICE") or os.environ.get("LOCAL_LLM_DEVICE")
    if explicit:
        return explicit.strip().lower()
    try:
        import torch
        if torch.cuda.is_available():
            return "gpu"
    except Exception:
        pass
    return "cpu"


LLM_DEVICE = _default_llm_device()
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

# Debug flag — when True, unhandled exception responses include the error
# detail string.  Keep False in production to avoid leaking internals.
DEBUG_ERRORS = _env_bool("DEBUG_ERRORS", False)

# Rate-limiter resilience — when True (default), a Redis/rate-limiter failure
# allows the request through.  Set to False in production to fail closed.
RATE_LIMIT_FAIL_OPEN = _env_bool("RATE_LIMIT_FAIL_OPEN", True)

# Audit privacy — command and response text remain excluded unless explicitly enabled.
AUDIT_LOG_COMMAND_TEXT = _env_bool("AUDIT_LOG_COMMAND_TEXT", False)

# Local voice. Models are installed explicitly; application startup never downloads them.
VOICES_DIR = os.path.join(DATA_DIR, "voices")


def _resolve_reference_audios() -> list[str]:
    env_refs = os.environ.get("VOICE_CLONE_REFERENCE_AUDIOS")
    if env_refs:
        paths = [p.strip() for p in env_refs.split(",") if p.strip()]
        return [p if os.path.isabs(p) else os.path.join(BASE_DIR, p) for p in paths]
    defaults = [
        os.path.join(VOICES_DIR, "reference.wav"),
        os.path.join(VOICES_DIR, "reference1.wav"),
    ]
    existing = [p for p in defaults if os.path.exists(p)]
    if existing:
        return existing
    if os.path.isdir(VOICES_DIR):
        wavs = [os.path.join(VOICES_DIR, f) for f in os.listdir(VOICES_DIR) if f.lower().endswith(".wav")]
        if wavs:
            return sorted(wavs)
    return []


VOICE_CLONE_REFERENCE_AUDIOS = _resolve_reference_audios()
VOICE_STT_PROVIDER = os.environ.get("VOICE_STT_PROVIDER", "vosk").strip().lower()


def _default_tts_provider() -> str:
    """Pick the best TTS provider based on available hardware.

    XTTS produces high-quality voice-cloned audio but is far too slow on CPU
    (5-15 s per sentence).  Only default to it when a CUDA GPU is available.
    """
    explicit = os.environ.get("VOICE_TTS_PROVIDER")
    if explicit:
        return explicit.strip().lower()

    if VOICE_CLONE_REFERENCE_AUDIOS:
        try:
            import torch
            if torch.cuda.is_available():
                return "xtts"
        except Exception:
            pass

    # Fast providers: piper (if model present), else Windows SAPI
    piper_model = os.path.join(LOCAL_TTS_DIR, "voice.onnx")
    if os.path.exists(piper_model) and shutil.which("piper"):
        return "piper"
    if os.name == "nt":
        return "sapi"
    return "piper"


VOICE_TTS_PROVIDER = _default_tts_provider()

VOSK_MODEL_PATH = os.environ.get("VOSK_MODEL_PATH", os.path.join(LOCAL_STT_DIR, "vosk-en-us"))
WHISPER_MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", os.path.join(LOCAL_STT_DIR, "whisper"))
PIPER_MODEL_PATH = os.environ.get("PIPER_MODEL_PATH", os.path.join(LOCAL_TTS_DIR, "voice.onnx"))
PIPER_EXECUTABLE = os.environ.get("PIPER_EXECUTABLE", "piper")
XTTS_MODEL_DIR = os.environ.get("XTTS_MODEL_DIR", os.path.join(LOCAL_TTS_DIR, "xtts_v2"))
XTTS_LANGUAGE = os.environ.get("XTTS_LANGUAGE", "en").strip().lower()
XTTS_USE_GPU = os.environ.get("XTTS_USE_GPU", "auto").strip().lower()
VOICE_MAX_UPLOAD_BYTES = int(os.environ.get("VOICE_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
VOICE_MAX_DURATION_SECONDS = float(os.environ.get("VOICE_MAX_DURATION_SECONDS", "30"))
VOICE_TTS_TIMEOUT_SECONDS = float(os.environ.get("VOICE_TTS_TIMEOUT_SECONDS", "15"))
DESKTOP_SUBPROCESS_TIMEOUT_SECONDS = float(
    os.environ.get("DESKTOP_SUBPROCESS_TIMEOUT_SECONDS", "5")
)

# Weather API (OpenWeatherMap)
OPENWEATHERMAP_API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "").strip()
OPENWEATHERMAP_DEFAULT_CITY = os.environ.get("OPENWEATHERMAP_DEFAULT_CITY", "Chennai").strip()
OPENWEATHERMAP_UNITS = os.environ.get("OPENWEATHERMAP_UNITS", "metric").strip().lower()

# Voice Latency & Streaming Settings
VOICE_LOW_LATENCY_MODE = _env_bool("VOICE_LOW_LATENCY_MODE", True)
VOICE_FAST_ACK_ENABLED = _env_bool("VOICE_FAST_ACK_ENABLED", True)
VOICE_FAST_ACK_PROVIDER = os.environ.get("VOICE_FAST_ACK_PROVIDER", "piper").strip().lower()
VOICE_LLM_MAX_TOKENS = int(os.environ.get("VOICE_LLM_MAX_TOKENS", "96"))
VOICE_STREAM_CHUNK_MIN_CHARS = int(os.environ.get("VOICE_STREAM_CHUNK_MIN_CHARS", "60"))
VOICE_STREAM_CHUNK_MAX_CHARS = int(os.environ.get("VOICE_STREAM_CHUNK_MAX_CHARS", "180"))

