
import os
import subprocess
import webbrowser
import datetime
import time
import logging
import urllib.parse
import psutil
import pyautogui
import config
import wikipedia
import pyjokes
import app_launcher

logger = logging.getLogger(__name__)

# Verbs that mean "open an app"
_OPEN_VERBS = ("open", "launch", "start", "run")
_CLOSE_VERBS = ("close", "kill", "stop", "quit", "exit")
_CONFIRM_YES = ("yes", "y", "ok", "okay", "confirm", "proceed", "do it")

# Website name → URL registry
_WEBSITES = {
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google maps": "https://maps.google.com",
    "google translate": "https://translate.google.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
    "twitch": "https://www.twitch.tv",
    "spotify": "https://open.spotify.com",
    "chatgpt": "https://chat.openai.com",
    "chat gpt": "https://chat.openai.com",
    "gemini": "https://gemini.google.com",
    "notion": "https://www.notion.so",
    "figma": "https://www.figma.com",
    "canva": "https://www.canva.com",
    "pinterest": "https://www.pinterest.com",
    "medium": "https://medium.com",
    "quora": "https://www.quora.com",
    "zoom": "https://zoom.us",
    "slack": "https://slack.com",
    "trello": "https://trello.com",
    "w3schools": "https://www.w3schools.com",
    "geeksforgeeks": "https://www.geeksforgeeks.org",
}


class Actions:
    def __init__(self, speech_engine):
        self.speak = speech_engine.speak
        # Command registry: list of (matcher, handler) tuples checked in order.
        # Each matcher is a callable(query) -> bool. First match wins.
        self._commands = [
            (self._match_play_youtube,   lambda q, **_: self.play_youtube(q)),
            (self._match_social_media,   self.open_social_media),
            (self._match_schedule,       lambda q, **_: self.schedule()),
            (self._match_time,           lambda q, **_: self.tell_time(q)),
            (self._match_volume,         lambda q, **_: self.volume_control(q)),
            (self._match_scroll,         lambda q, **_: self.scroll_navigate(q)),
            (self._match_tab,            lambda q, **_: self.tab_management(q)),
            (self._match_open_website,   lambda q, **_: self.open_website(q)),
            (self._match_open_app,       lambda q, **_: self.open_app(q)),
            (self._match_close_app,      lambda q, **_: self.close_app(q)),
            (self._match_browse,         self._handle_browse),
            (self._match_system,         lambda q, **_: self.system_condition()),
            (self._match_wikipedia,      lambda q, **_: self.search_wikipedia(q)),
            (self._match_screenshot,     lambda q, **_: self.take_screenshot()),
            (self._match_joke,           lambda q, **_: self.tell_joke()),
            (self._match_exit,           self._handle_exit),
        ]

    # ── Matchers ─────────────────────────────────────────────────────
    @staticmethod
    def _match_social_media(q):
        return any(p in q for p in ('facebook', 'discord', 'whatsapp', 'instagram', 'youtube'))

    @staticmethod
    def _match_schedule(q):
        return "university time table" in q or "schedule" in q

    @staticmethod
    def _match_time(q):
        return any(w in q for w in ("time", "date", "month"))

    @staticmethod
    def _match_volume(q):
        return "volume" in q or "mute" in q

    @staticmethod
    def _match_open_website(q):
        has_verb = any(v in q for v in ("open", "go to", "visit", "navigate to"))
        has_site = any(site in q for site in _WEBSITES)
        return has_verb and has_site

    @staticmethod
    def _match_open_app(q):
        return any(v in q for v in _OPEN_VERBS) and not any(s in q for s in ('google', 'youtube', 'facebook', 'whatsapp', 'discord', 'instagram'))

    @staticmethod
    def _match_close_app(q):
        # Must have a close verb and something to close (not just "exit" or "quit" alone)
        words = q.split()
        has_close_verb = any(v in q for v in ("close", "kill", "stop"))
        has_target = len(words) >= 2  # "close chrome" = 2 words minimum
        return has_close_verb and has_target

    @staticmethod
    def _match_browse(q):
        return any(w in q for w in ("google", "edge", "search"))

    @staticmethod
    def _match_system(q):
        return "system condition" in q or "condition of the system" in q

    @staticmethod
    def _match_wikipedia(q):
        return "wikipedia" in q

    @staticmethod
    def _match_screenshot(q):
        return "screenshot" in q

    @staticmethod
    def _match_joke(q):
        return "joke" in q

    @staticmethod
    def _match_play_youtube(q):
        return "play" in q and "youtube" in q

    @staticmethod
    def _match_exit(q):
        # Only match standalone "exit" / "quit" or "exit meero" — not "exit chrome"
        stripped = q.strip()
        return stripped in ("exit", "quit", "exit meero", "quit meero", "goodbye", "bye")

    @staticmethod
    def _match_scroll(q):
        return any(w in q for w in (
            "scroll up", "scroll down", "page up", "page down",
            "go back", "go forward", "go to top", "go to bottom",
            "scroll to top", "scroll to bottom"
        ))

    @staticmethod
    def _match_tab(q):
        return any(w in q for w in (
            "new tab", "close tab", "next tab", "previous tab",
            "switch tab", "close this tab"
        ))

    # ── Helpers ──────────────────────────────────────────────────────
    def cal_day(self):
        return datetime.datetime.today().strftime("%A")

    # ── Open Website by Name ────────────────────────────────────────
    def open_website(self, command):
        # Find which website name is in the command (check longest names first)
        for site_name in sorted(_WEBSITES, key=len, reverse=True):
            if site_name in command:
                url = _WEBSITES[site_name]
                self.speak(f"Opening {site_name.capitalize()}")
                webbrowser.open(url)
                return
        self.speak("I couldn't identify that website.")

    # ── Scroll / Navigate ───────────────────────────────────────────
    def scroll_navigate(self, command):
        if "scroll down" in command or "page down" in command:
            pyautogui.scroll(-5)  # Negative = scroll down
            self.speak("Scrolling down")
        elif "scroll up" in command or "page up" in command:
            pyautogui.scroll(5)   # Positive = scroll up
            self.speak("Scrolling up")
        elif "go to top" in command or "scroll to top" in command:
            pyautogui.hotkey('ctrl', 'Home')
            self.speak("Going to top")
        elif "go to bottom" in command or "scroll to bottom" in command:
            pyautogui.hotkey('ctrl', 'End')
            self.speak("Going to bottom")
        elif "go back" in command:
            pyautogui.hotkey('alt', 'Left')
            self.speak("Going back")
        elif "go forward" in command:
            pyautogui.hotkey('alt', 'Right')
            self.speak("Going forward")

    # ── Tab Management ──────────────────────────────────────────────
    def tab_management(self, command):
        if "new tab" in command:
            pyautogui.hotkey('ctrl', 't')
            self.speak("Opening new tab")
        elif "close tab" in command or "close this tab" in command:
            pyautogui.hotkey('ctrl', 'w')
            self.speak("Closing tab")
        elif "next tab" in command or "switch tab" in command:
            pyautogui.hotkey('ctrl', 'Tab')
            self.speak("Switching to next tab")
        elif "previous tab" in command:
            pyautogui.hotkey('ctrl', 'shift', 'Tab')
            self.speak("Switching to previous tab")

    def wish_me(self):
        hour = int(datetime.datetime.now().hour)
        t = time.strftime("%I:%M %p")
        day = self.cal_day()
        
        greeting = "Good evening"
        if 0 <= hour <= 12:
            greeting = "Good morning"
        elif 12 < hour <= 16:
            greeting = "Good afternoon"
            
        self.speak(f"{greeting} Mr. {config.USER_NAME}. It is {day}, {t}. Systems are online and ready.")

    # ── Action Handlers ──────────────────────────────────────────────
    def open_social_media(self, command, **_kwargs):
        if "close" in command:
             self.speak("Closing current tab immediately, sir.")
             pyautogui.hotkey('ctrl', 'w')
             return

        for platform, url in config.SOCIAL_MEDIA_URLS.items():
            if platform in command:
                self.speak(f"Accessing {platform.capitalize()}, sir.")
                webbrowser.open(url)
                return

        self.speak("I could not identify that social media platform, sir.")

    def schedule(self):
        day = self.cal_day().lower()
        self.speak(f"Boss, today is {day.capitalize()}. Here is your schedule.")
        
        if day in config.SCHEDULE:
            self.speak(config.SCHEDULE[day])
        else:
            self.speak("You have no schedule for today.")

    def open_app(self, command):
        # Extract the app name by removing known verb phrases
        app_name = command
        for phrase in ("open", "launch", "start", "run", "please", "can you", "could you"):
            app_name = app_name.replace(phrase, "")
        app_name = app_name.strip()

        if not app_name:
            self.speak("What application should I open?")
            return

        # Try hardcoded fast paths first
        hardcoded = {
            "calculator": config.CALCULATOR_PATH,
            "notepad": config.NOTEPAD_PATH,
            "paint": config.PAINT_PATH,
        }
        for name, path in hardcoded.items():
            if name in app_name:
                self.speak(f"Opening {name}")
                os.startfile(path)
                return

        if "vscode" in app_name or "visual studio code" in app_name:
            self.speak("Opening Visual Studio Code")
            subprocess.Popen([config.VSCODE_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return

        # Dynamic lookup — finds any installed app
        self.speak(f"Looking for {app_name}...")
        success, message = app_launcher.find_and_open_app(app_name)
        self.speak(message)

    def close_app(self, command):
        # Extract the app name by removing known verb phrases
        app_name = command
        for phrase in ("close", "kill", "stop", "quit", "exit", "please", "can you", "could you", "the"):
            app_name = app_name.replace(phrase, "")
        app_name = app_name.strip()

        if not app_name:
            self.speak("What application should I close?")
            return

        # Dynamic close — works for any app
        success, message = app_launcher.close_app_by_name(app_name)
        self.speak(message)

    def browse(self, query, input_func):
        search_term = query.replace("open google", "").replace("google search", "").replace("google", "").replace("search for", "").replace("search", "").replace("browse", "").strip()
        
        if not search_term:
            self.speak("Boss, what should I search for?")
            search_term = input_func()
        
        if search_term != "None":
            self.speak(f"Searching for {search_term}")
            if 'edge' in query:
                webbrowser.open(f"https://www.bing.com/search?q={urllib.parse.quote_plus(search_term)}")
            else:
                webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(search_term)}")

    def _handle_browse(self, query, input_func=None, **_kwargs):
        self.browse(query, input_func)

    def volume_control(self, command):
        if "up" in command or "increase" in command:
            pyautogui.press("volumeup")
            self.speak("Volume increased")
        elif "down" in command or "decrease" in command:
            pyautogui.press("volumedown")
            self.speak("Volume decrease")
        elif "mute" in command:
            pyautogui.press("volumemute")
            self.speak("Volume muted")

    def system_condition(self):
        usage = str(psutil.cpu_percent())
        self.speak(f"CPU is at {usage} percentage")
        
        battery = psutil.sensors_battery()
        if battery:
            percentage = battery.percent
            self.speak(f"Boss our system has {percentage} percentage battery")
            if percentage >= 80:
                self.speak("We have enough charge.")
            elif 40 <= percentage <= 75:
                self.speak("We should connect to a charger soon.")
            else:
                self.speak("Critical battery level, please connect charger.")
        else:
            self.speak("Battery information is not available for this system.")

    def search_wikipedia(self, query):
        self.speak("Searching Wikipedia...")
        query = query.replace("wikipedia", "").replace("search wikipedia", "").replace("who is", "").replace("tell me about", "")
        try:
            results = wikipedia.summary(query, sentences=2)
            self.speak("According to Wikipedia")
            logger.info("Wikipedia result: %s", results)
            self.speak(results)
        except Exception:
            self.speak("Found nothing on Wikipedia.")

    def take_screenshot(self):
        self.speak("Taking screenshot")
        img = pyautogui.screenshot()
        name = time.time()
        img.save(f"{name}.png")
        self.speak("Screenshot saved")

    def tell_joke(self):
        joke = pyjokes.get_joke()
        logger.info("Joke: %s", joke)
        self.speak(joke)

    def tell_time(self, query):
        now = datetime.datetime.now()
        if "time" in query:
            t = now.strftime("%I:%M %p")
            self.speak(f"The time is {t}")
        if "date" in query:
            d = now.strftime("%B %d, %Y")
            self.speak(f"Today's date is {d}")
        if "month" in query:
            m = now.strftime("%B")
            self.speak(f"It is {m}")

    def play_youtube(self, query):
        song = query.replace("play", "").replace("on youtube", "").strip()
        self.speak(f"Playing {song} on YouTube")
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(song)}")

    def _handle_exit(self, query, exit_func=None, **_kwargs):
        self.speak("Goodbye boss.")
        if exit_func:
            exit_func()
        else:
            os._exit(0)

    def _requires_confirmation(self, query):
        q = query.lower().strip()
        destructive_keywords = (
            "delete", "remove", "format", "wipe", "reset",
            "uninstall", "shutdown", "restart", "registry"
        )

        # Treat system-level changes as sensitive operations.
        is_destructive = any(k in q for k in destructive_keywords)
        is_settings_change = "settings" in q
        is_app_termination = self._match_close_app(q) and "notepad" not in q
        return is_destructive or is_settings_change or is_app_termination

    def _confirm_sensitive_action(self, input_func):
        self.speak("This action may delete data or change system settings. Should I continue? Say yes or no.")
        if not input_func:
            self.speak("I could not get your confirmation. Action cancelled.")
            return False

        answer = (input_func() or "").strip().lower()
        if answer in _CONFIRM_YES:
            return True

        self.speak("Action cancelled.")
        return False

    # ── Main Dispatcher ──────────────────────────────────────────────
    def process_command(self, query, input_func=None, exit_func=None):
        if not query or query == "None":
            return

        for matcher, handler in self._commands:
            if matcher(query):
                if self._requires_confirmation(query):
                    if not self._confirm_sensitive_action(input_func):
                        return "action_cancelled"
                handler(query, input_func=input_func, exit_func=exit_func)
                return

        return "neural_net_fallback"  # Signal to caller to use neural net
