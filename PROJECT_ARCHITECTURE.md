# Project Architecture: Meero Python 2.0

## 1. Frontend (User Interface)
The frontend is built with **React (+Vite)** to provide a modern, interactive, and voice-enabled user interface.

### **Tech Stack**
-   **Framework**: React 19 (via Vite 7.3)
-   **Styling**: Tailwind CSS v4, Vanilla CSS
-   **Animations**: Framer Motion
-   **Icons**: Lucide React
-   **State Management**: React Hooks (`useState`, `useEffect`, `useRef`, `useCallback`)
-   **Communication**: Axios for HTTP requests

### **Key Components**
-   **`App.jsx`**: The main controller. Handles:
    -   Web Speech API (Speech-to-Text)
    -   Web Speech Synthesis (Text-to-Speech)
    -   UI State Management (Idle / Listening / Processing / Speaking)
    -   Connecting to Backend API (`/command`)
-   **`VoiceOrb.jsx`**: An animated visualizer that changes state (colors, pulsing) based on whether the bot is listening, processing, or speaking.
-   **`Typewriter.jsx`**: Renders bot responses character-by-character for a natural AI feel.
-   **`Background.jsx`**: Provides a cinematic, animated deep-space gradient background.

---

## 2. Backend (Logic & Intelligence)
The backend is a **python-based** REST API that handles command processing, system automation, and NLP.

### **Tech Stack**
-   **Framework**: FastAPI
-   **Server**: Uvicorn
-   **ML/AI**: TensorFlow (Keras), Scikit-Learn (LabelEncoder)
-   **NLP**: NLTK (via `intents.json` dataset - assumed), Pickle (for tokenizer)
-   **Automation**: PyAutoGUI, OS, Webbrowser, Psutil

### **Key Modules**
1.  **`server.py` (Entry Point)**
    -   Runs the FastAPI server on `localhost:8000`.
    -   Exposes the `POST /command` endpoint.
    -   Coordinates between the Rule-Based Engine (`Actions`) and the Neural Network (`NeuralNet`).

2.  **`actions.py` (Rule-Based Engine)**
    -   Handles explicit commands where precision is key.
    -   **Web Automation**: Opens Facebook, YouTube, WhatsApp, etc.
    -   **System Control**: Volume control, Screenshot, Launch/Close Apps (Notepad, Calc, Paint).
    -   **Information**: Time, Date, Day, Wikipedia Search, System Stats (Battery/CPU).
    -   **Mock IO**: Uses `MockSpeechEngine` to capture text responses to send back to the frontend.

3.  **`neural_net.py` (AI Engine)**
    -   **Fallback Mechanism**: If no specific rule matches in `actions.py`, this engine is called.
    -   **Model**: Loads a pre-trained Keras model (`chat_model.h5`).
    -   **Logic**: Tokenizes the user query, predicts user intent from `intents.json`, and returns a randomized natural language response (e.g., greetings, small talk).

### **Legacy / Standalone**
-   **`main.py`**: The original entry point for running Meero locally without a frontend. It initializes the `SpeechEngine` and `Actions` directly, listening to the microphone in an infinite loop.

### **Support Modules**
-   **`mock_engine.py`**: A lightweight class that mimics the functionality of a speech engine but captures text output instead of speaking it aloud. This is critical for the API (server.py) to return text responses to the frontend.
-   **`config.py`**: Central configuration file storing file paths, constants (Voice Index, Speech Rate), and user settings.
-   **`speech_engine.py`**: The legacy/desktop engine handling local PyAudio and PyTTSx3. Used by `main.py`.

### **Training & Data**
-   **`model_train.py`**: The script used to train the Neural Network. It processes `intents.json`, tokenizes words, and dumps the trained model.
-   **`model_test.py`**: A CLI script to manually test the trained Neural Network (text-only mode) without spinning up the full Assistant.
-   **`intents.json`**: The dataset containing patterns (inputs) and responses (outputs) for the AI.
-   **`requirements.txt`**: List of all Python dependencies.

## 3. Integration Data Flow
1.  **User Speaks** -> Frontend (Web Speech API) -> Text.
2.  **Request**: Frontend sends Text to Backend (`POST /command`).
3.  **Processing**:
    -   `server.py` checks `actions.py` first (e.g., "Open Youtube").
    -   If no match, it queries `neural_net.py` (e.g., "How are you?").
4.  **Response**: Backend sends text response back to Frontend.
5.  **Output**: Frontend displays text (Typewriter) and speaks it (Speech Synthesis).
