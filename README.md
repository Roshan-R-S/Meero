# Meero Python 2.0 (AI Assistant)

A modern, voice-activated virtual assistant powered by a Python backend (TensorFlow/FastAPI) and a React frontend. Meero can perform system automation, web browsing, and hold conversations using a trained neural network.

## 🚀 Features

*   **Voice Interaction**: Full speech-to-text and text-to-speech capabilities.
*   **Web Dashboard**: A beautiful, animated UI built with React, Tailwind CSS, and Framer Motion.
*   **Intelligence**: Neural Network (Keras) for natural language understanding.
*   **Automation**:
    *   Open/Close Apps (Notepad, Calculator, Paint).
    *   Social Media Shortcuts (YouTube, Facebook, WhatsApp).
    *   System Control (Volume, Battery, CPU).
    *   Information (Time, Date, Wikipedia).

## 🏗️ Architecture

For a detailed breakdown of all 8+ modules, please see [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md).

### **High Level**
*   **Frontend**: React + Vite (Port 5173). Handles audio IO and visuals.
*   **Backend**: Python FastAPI (Port 8000). Handles logic and automation.

## 🛠️ Installation

### 1. Prerequisites
*   Python 3.8+
*   Node.js & npm

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

## ▶️ Usage

### Running the Project (Integrated Mode)

1.  **Start the Backend**:
    ```bash
    # Root directory
    python server.py
    ```
2.  **Start the Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```
3.  **Open Browser**: Visist `http://localhost:5173`.

### Training the Model
If you modify `intents.json`, retrain the AI:
```bash
python model_train.py
```

### Running in Legacy Mode (Console Only)
To run without the web UI:
```bash
python main.py
```

## Offline Speech Recognition (Vosk)

Meero supports an offline STT backend using Vosk. By default the project prefers Vosk when available and falls back to Google Online STT.

- **Install**: Vosk is already included in `requirements.txt`; install with:

```powershell
pip install -r requirements.txt
```

- **Download a Vosk model**: use the setup helper to download, safely extract, and verify the default small English model:

```powershell
python scripts/setup_vosk.py
python scripts/setup_vosk.py --verify-only
```

- **Configure**: either place the model under `models/vosk-model-small` (default) or set the `VOSK_MODEL_PATH` environment variable to the model folder. To force Google recognizer instead, set `SPEECH_BACKEND` to `google`.

```powershell
# Point to a custom model path for the current session
$env:VOSK_MODEL_PATH = "E:\path\to\models\vosk-model-small-en-us-0.15"
# Or force online Google backend
$env:SPEECH_BACKEND = "google"
```

- **Notes**:
    - Vosk runs fully offline but requires downloading a language model (tens to hundreds of MB).
    - If Vosk fails or is unavailable, Meero will automatically fall back to the Google recognizer.

## Model Packaging and Release Automation

Build versioned intent-model artifacts locally:

```powershell
python scripts/train_and_package.py --epochs 5 --batch 32 --out-dir build/model-artifacts
```

Quantize a Hugging Face model directory or source GGUF with llama.cpp tools:

```powershell
python scripts/package_gguf.py --input path\to\hf-model --out-dir build\model-artifacts\gguf --quantization Q4_K_M
```

Tagged pushes (`v*`) and published GitHub releases build/package artifacts, attach them to the workflow/release, and optionally publish to Hugging Face when `HF_TOKEN` and `HF_REPO` secrets are configured.

## Security and Formatting

Install local hooks:

```powershell
pip install -r requirements-test.txt
pre-commit install
```

Run the secret scanner manually:

```powershell
python scripts/secret_scan.py
```

Rotate GitHub Actions secrets with the helper by setting replacement values in `NEW_<SECRET_NAME>` environment variables, for example `NEW_HF_TOKEN`, then running:

```powershell
python scripts/rotate_tokens.py --secret HF_TOKEN --repo owner/repo
```
