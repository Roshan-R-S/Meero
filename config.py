
import os
import json
import shutil

# Assistant Settings
ASSISTANT_NAME = "Meero"
USER_NAME = "Roshan"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
LLM_MODEL_PATH = os.path.join(BASE_DIR, "models", "Llama-3.2-1B-Instruct-Q4_K_M.gguf")

# Feature flags
# Set to False to disable loading/using the neural net or local LLM fallback
USE_NEURAL_NET = True
USE_LLM = True

# Neural net confidence threshold (0.0 - 1.0) used to decide whether to use the
# neural net's answer or fall back to the LLM. Keep high if you prefer LLMs.
NEURAL_NET_CONFIDENCE_THRESHOLD = 0.8

# LLM generation timeout (seconds) — used by async or guarded calls.
LLM_MAX_GENERATION_TIME = 10

# Remote provider name (optional) — e.g., 'openai', 'google', or None for local
LLM_API_PROVIDER = None

# Speech Settings
VOICE_INDEX = 1  # Index of the voice to use
SPEECH_RATE_OFFSET = -50
VOLUME_OFFSET = 0.25
ENERGY_THRESHOLD = 4000

# Neural Net Hyperparameters (shared between training and inference)
NEURAL_NET_MAXLEN = 20
NEURAL_NET_VOCAB_SIZE = 1000
NEURAL_NET_EMBEDDING_DIM = 16
