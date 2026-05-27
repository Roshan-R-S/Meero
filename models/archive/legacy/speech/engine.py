import json
import logging
import os

import config

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:
    sr = None

_has_vosk = False
try:
    from vosk import Model, KaldiRecognizer
    _has_vosk = True
except Exception:
    Model = None
    KaldiRecognizer = None
    _has_vosk = False

logger = logging.getLogger(__name__)


class SpeechEngine:
    def __init__(self):
        if pyttsx3 is None:
            logger.warning("pyttsx3 unavailable, TTS disabled")
            self._engine = None
            return

        try:
            self._engine = pyttsx3.init("sapi5")
            voices = self._engine.getProperty('voices')
            try:
                self._engine.setProperty('voice', voices[config.VOICE_INDEX].id)
            except IndexError:
                self._engine.setProperty('voice', voices[0].id)

            self._engine.setProperty('rate', self._engine.getProperty('rate') + config.SPEECH_RATE_OFFSET)
            self._engine.setProperty('volume', self._engine.getProperty('volume') + config.VOLUME_OFFSET)
        except Exception:
            logger.exception("Failed to initialize TTS engine")
            self._engine = None

    def speak(self, text):
        logger.info("Meero: %s", text)
        if self._engine is None:
            logger.warning("TTS engine unavailable, skipping speech")
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except RuntimeError:
            logger.warning("TTS engine busy, reinitializing")
            try:
                self._engine = pyttsx3.init("sapi5")
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                logger.exception("TTS retry failed")

    def _capture_audio(self):
        if sr is None:
            raise RuntimeError("speech_recognition unavailable")

        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            logger.info("Listening...")
            if hasattr(recognizer, "adjust_for_ambient_noise"):
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            recognizer.pause_threshold = 1.0
            recognizer.energy_threshold = config.ENERGY_THRESHOLD
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                logger.info("Listen timeout")
                return recognizer, None
        return recognizer, audio

    def _resolve_vosk_model_path(self):
        model_path = config.VOSK_MODEL_PATH
        if not model_path:
            raise RuntimeError("Vosk model not configured")

        required = ("am", "conf", "graph")
        if all(os.path.isdir(os.path.join(model_path, name)) for name in required):
            return model_path

        if os.path.isdir(model_path):
            for name in os.listdir(model_path):
                candidate = os.path.join(model_path, name)
                if all(os.path.isdir(os.path.join(candidate, part)) for part in required):
                    return candidate

        raise RuntimeError(f"Vosk model files not found under {model_path}")

    def listen(self):
        if config.SPEECH_RECOGNITION_BACKEND == 'vosk' and _has_vosk:
            try:
                if Model is None or KaldiRecognizer is None:
                    raise RuntimeError("Vosk package not available")

                _, audio = self._capture_audio()
                if audio is None:
                    return "None"

                model_path = self._resolve_vosk_model_path()
                raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                model = Model(model_path)
                rec = KaldiRecognizer(model, 16000)
                rec.AcceptWaveform(raw_data)
                result = rec.Result()
                text = json.loads(result).get('text', '')
                logger.info("Vosk recognized: %s", text)
                return text.lower() if text else "None"
            except Exception:
                logger.exception("Vosk recognition failed, falling back to Google")

        try:
            r, audio = self._capture_audio()
        except Exception:
            logger.exception("Microphone capture failed")
            return "None"

        if audio is None:
            return "None"

        try:
            logger.info("Recognizing (Google)...")
            query = r.recognize_google(audio, language='en-in')
            logger.info("User said: %s", query)
            return query.lower()
        except sr.UnknownValueError:
            return "None"
        except sr.RequestError:
            logger.error("Speech recognition network error")
            return "None"
        except Exception:
            logger.exception("Speech recognition error")
            return "None"

    def get_input(self, input_mode="voice"):
        if input_mode == "text":
            return input("You: ").lower()
        else:
            return self.listen()
