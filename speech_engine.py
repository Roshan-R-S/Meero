
import logging
import pyttsx3
import speech_recognition as sr
import config

_has_vosk = False
try:
    from vosk import Model, KaldiRecognizer
    import json
    _has_vosk = True
except Exception:
    _has_vosk = False

logger = logging.getLogger(__name__)


class SpeechEngine:
    def __init__(self):
        """Initialize the TTS engine once and reuse it."""
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
            # Engine loop already running — re-init and retry once
            logger.warning("TTS engine busy, reinitializing")
            try:
                self._engine = pyttsx3.init("sapi5")
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                logger.exception("TTS retry failed")

    def listen(self):
        """Listen using configured backend (Vosk offline preferred, Google fallback)."""
        # If Vosk is configured and available, use it (offline)
        if config.SPEECH_RECOGNITION_BACKEND == 'vosk' and _has_vosk:
            try:
                model_path = config.VOSK_MODEL_PATH
                if not model_path or not Model:
                    raise RuntimeError("Vosk model not configured")

                # Use PyAudio via speech_recognition microphone capture
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    logger.info("Listening (Vosk)...")
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=5, phrase_time_limit=10)

                # Convert to raw bytes for Vosk
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

        # Fallback: speech_recognition with Google (online)
        r = sr.Recognizer()
        with sr.Microphone() as source:
            logger.info("Listening...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            r.pause_threshold = 1.0
            r.energy_threshold = config.ENERGY_THRESHOLD
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                logger.info("Listen timeout")
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
        """Wrapper to get input either from voice or text"""
        if input_mode == "text":
            return input("You: ").lower()
        else:
            return self.listen()
