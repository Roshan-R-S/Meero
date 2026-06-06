import datetime
import logging
import os
import re
import subprocess
import time
import urllib.parse
import webbrowser

import app_launcher
import config
import pyjokes
import psutil
import wikipedia
from .actions_routing import COMMAND_ROUTE_SPECS, match_any_phrase, match_regex

logger = logging.getLogger(__name__)


class _UnavailablePyAutoGUI:
    def __getattr__(self, name):
        def _missing(*_args, **_kwargs):
            raise RuntimeError("pyautogui is unavailable in this environment")

        return _missing


try:
    import pyautogui
except Exception:
    logger.info("pyautogui unavailable; GUI automation commands are disabled")
    pyautogui = _UnavailablePyAutoGUI()


def start_file(path):
    if not hasattr(os, "startfile"):
        raise RuntimeError("os.startfile is only available on Windows")
    os.startfile(path)


_OPEN_VERBS = ("open", "launch", "start", "run")
_CLOSE_VERBS = ("close", "kill", "stop", "quit", "exit")
_CONFIRM_YES = ("yes", "y", "ok", "okay", "confirm", "proceed", "do it")
_GREETING_RE = re.compile(
    r"^(hi|hello|hey|yo|good morning|good afternoon|good evening)(\s+meero)?[.!?]*$",
    re.IGNORECASE,
)

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
    def __init__(self, response_engine):
        self.speak = response_engine.speak
        self._command_routes = self._build_command_routes()

    def _build_command_routes(self):
        no_arg_handlers = {
            "greet": lambda q: self.greet(),
            "schedule": lambda q: self.schedule(),
            "system_condition": lambda q: self.system_condition(),
            "take_screenshot": lambda q: self.take_screenshot(),
            "tell_joke": lambda q: self.tell_joke(),
        }
        query_handlers = {
            "play_youtube": lambda q: self.play_youtube(q),
            "tell_time": lambda q: self.tell_time(q),
            "volume_control": lambda q: self.volume_control(q),
            "scroll_navigate": lambda q: self.scroll_navigate(q),
            "tab_management": lambda q: self.tab_management(q),
            "open_website": lambda q: self.open_website(q),
            "open_app": lambda q: self.open_app(q),
            "close_app": lambda q: self.close_app(q),
            "search_wikipedia": lambda q: self.search_wikipedia(q),
        }

        routes = []
        for spec in COMMAND_ROUTE_SPECS:
            if spec.matcher:
                matcher = getattr(self, spec.matcher)
            else:
                compiled = tuple(re.compile(pattern, re.IGNORECASE) for pattern in spec.patterns)

                def matcher(query, _compiled=compiled):
                    return any(pattern.search(query) for pattern in _compiled)

            if spec.handler in no_arg_handlers:
                handler = no_arg_handlers[spec.handler]
            elif spec.handler in query_handlers:
                handler = query_handlers[spec.handler]
            else:
                handler = getattr(self, spec.handler)

            routes.append((matcher, handler))
        return routes

    @staticmethod
    def _match_any_phrase(q, phrases):
        return match_any_phrase(q, phrases)

    @staticmethod
    def _match_regex(q, pattern):
        return match_regex(q, pattern)

    @staticmethod
    def _match_social_media(q):
        return Actions._match_any_phrase(q, ('facebook', 'discord', 'whatsapp', 'instagram', 'youtube'))

    @staticmethod
    def _match_greeting(q):
        return bool(_GREETING_RE.match(q.strip().lower()))

    @staticmethod
    def _match_schedule(q):
        return Actions._match_any_phrase(q, ("university time table", "schedule"))

    @staticmethod
    def _match_time(q):
        return Actions._match_any_phrase(q, ("time", "date", "month"))

    @staticmethod
    def _match_volume(q):
        return Actions._match_any_phrase(q, ("volume", "mute"))

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
        words = q.split()
        has_close_verb = any(v in q for v in ("close", "kill", "stop"))
        has_target = len(words) >= 2
        return has_close_verb and has_target

    @staticmethod
    def _match_browse(q):
        return Actions._match_any_phrase(q, ("google", "edge", "search"))

    @staticmethod
    def _match_system(q):
        return Actions._match_any_phrase(q, ("system condition", "condition of the system"))

    @staticmethod
    def _match_wikipedia(q):
        return Actions._match_any_phrase(q, ("wikipedia",))

    @staticmethod
    def _match_screenshot(q):
        return Actions._match_any_phrase(q, ("screenshot",))

    @staticmethod
    def _match_joke(q):
        return Actions._match_any_phrase(q, ("joke",))

    @staticmethod
    def _match_play_youtube(q):
        return Actions._match_regex(q, r"\bplay\b.*\byoutube\b")

    @staticmethod
    def _match_exit(q):
        stripped = q.strip()
        return stripped in ("exit", "quit", "exit meero", "quit meero", "goodbye", "bye")

    @staticmethod
    def _match_scroll(q):
        return Actions._match_any_phrase(q, (
            "scroll up", "scroll down", "page up", "page down",
            "go back", "go forward", "go to top", "go to bottom",
            "scroll to top", "scroll to bottom"
        ))

    @staticmethod
    def _match_tab(q):
        return Actions._match_any_phrase(q, (
            "new tab", "close tab", "next tab", "previous tab",
            "switch tab", "close this tab"
        ))

    def cal_day(self):
        return datetime.datetime.today().strftime("%A")

    def open_website(self, command):
        for site_name in sorted(_WEBSITES, key=len, reverse=True):
            if site_name in command:
                url = _WEBSITES[site_name]
                self.speak(f"Opening {site_name.capitalize()}")
                webbrowser.open(url)
                return
        self.speak("I couldn't identify that website.")

    def scroll_navigate(self, command):
        if "scroll down" in command or "page down" in command:
            pyautogui.scroll(-5)
            self.speak("Scrolling down")
        elif "scroll up" in command or "page up" in command:
            pyautogui.scroll(5)
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

    def tab_management(self, command):
        if "new tab" in command:
            # If the command includes a search request, open a search URL
            m = re.search(r"(?:search for|search|google)\s+(.+)$", command, re.IGNORECASE)
            if m:
                search_term = m.group(1).strip()
                if search_term:
                    self.speak(f"Searching for {search_term}")
                    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_term)}"
                    try:
                        webbrowser.open(url, new=2)
                    except Exception:
                        logger.exception("Failed to open browser for search")
                    return
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
        app_name = command
        for phrase in ("open", "launch", "start", "run", "please", "can you", "could you"):
            app_name = app_name.replace(phrase, "")
        app_name = app_name.strip()

        if not app_name:
            self.speak("What application should I open?")
            return

        hardcoded = {
            "calculator": config.CALCULATOR_PATH,
            "notepad": config.NOTEPAD_PATH,
            "paint": config.PAINT_PATH,
        }
        for name, path in hardcoded.items():
            if name in app_name:
                if not app_launcher.is_app_allowed(name):
                    self.speak(f"Opening {name} is not allowed by APP_LAUNCH_ALLOWLIST.")
                    return
                self.speak(f"Opening {name}")
                start_file(path)
                return

        if "vscode" in app_name or "visual studio code" in app_name:
            if not app_launcher.is_app_allowed("vscode"):
                self.speak("Opening vscode is not allowed by APP_LAUNCH_ALLOWLIST.")
                return
            self.speak("Opening Visual Studio Code")
            subprocess.Popen([config.VSCODE_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return

        self.speak(f"Looking for {app_name}...")
        success, message = app_launcher.find_and_open_app(app_name)
        self.speak(message)

    def close_app(self, command):
        app_name = command
        for phrase in ("close", "kill", "stop", "quit", "exit", "please", "can you", "could you", "the"):
            app_name = app_name.replace(phrase, "")
        app_name = app_name.strip()

        if not app_name:
            self.speak("What application should I close?")
            return

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
        os.makedirs("data/screenshots", exist_ok=True)
        filename = f"screenshot-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.png"
        filepath = os.path.join("data", "screenshots", filename)
        img.save(filepath)
        self.speak("Screenshot saved")
        return {"metadata": {"screenshot_path": filepath}}

    def tell_joke(self):
        joke = pyjokes.get_joke()
        logger.info("Joke: %s", joke)
        self.speak(joke)

    def greet(self):
        self.speak("I'm here to help. What can I assist you with today?")

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

    def process_command(self, query, input_func=None, exit_func=None):
        if not query or query == "None":
            return

        if self._requires_confirmation(query):
            if not self._confirm_sensitive_action(input_func):
                return "action_cancelled"

        for matcher, handler in self._command_routes:
            if matcher(query):
                return self._invoke_route(handler, query, input_func=input_func, exit_func=exit_func)

        return "neural_net_fallback"

    @staticmethod
    def _invoke_route(handler, query, input_func=None, exit_func=None):
        try:
            return handler(query, input_func=input_func, exit_func=exit_func)
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc):
                raise
            return handler(query)
