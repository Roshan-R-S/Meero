
import logging
import pyttsx3
import speech_recognition as sr
import config

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
        """Standard Speech Recognition"""
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
            logger.info("Recognizing...")
            query = r.recognize_google(audio, language='en-in')
            logger.info("User said: %s", query)
            return query.lower()
        except sr.UnknownValueError:
            # Speech was unintelligible
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
