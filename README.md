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
