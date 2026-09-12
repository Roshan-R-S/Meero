from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CommandRouteSpec:
    name: str
    handler: str
    patterns: tuple[str, ...] = ()
    matcher: str | None = None


def match_any_phrase(query: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in query for phrase in phrases)


def match_regex(query: str, pattern: str) -> bool:
    return bool(re.search(pattern, query, re.IGNORECASE))


COMMAND_ROUTE_SPECS = (
    CommandRouteSpec(name="greeting", handler="greet", patterns=(r"^(hi+|hey+|hello+|yo+|hiya|what'?s up|sup|good morning|good afternoon|good evening)(\s+meero)?[.!?]*$",)),
    CommandRouteSpec(name="how_are_you", handler="respond_how_are_you", patterns=(r"^how (are you|do you do|is it going|are things).*$", r"^how('?s| is) (everything|life).*$")),
    CommandRouteSpec(name="thanks", handler="respond_thanks", patterns=(r"^(thanks?( you)?|thank you( so much| very much)?|appreciate it|cheers)[\s.!?]*$",)),
    CommandRouteSpec(name="compliment", handler="respond_compliment", patterns=(r"^(you('?re| are) (great|awesome|the best|amazing|wonderful|helpful)|good (job|work)|well done|nice)[\s.!?]*$",)),
    CommandRouteSpec(name="farewell", handler="respond_farewell", patterns=(r"^(see you( later)?|take care|have a (good|nice) (day|night|one)|good night|later|peace( out)?)[\s.!?]*$",)),
    CommandRouteSpec(name="who_are_you", handler="respond_identity", patterns=(r"^(who are you|what are you|what('?s| is) your name|tell me about yourself)[\s.!?]*$",)),
    CommandRouteSpec(name="media_control", handler="handle_media_control", matcher="_match_media_control"),
    CommandRouteSpec(name="reminder", handler="handle_reminder", matcher="_match_reminder"),
    CommandRouteSpec(name="window_management", handler="handle_window_management", matcher="_match_window_management"),
    CommandRouteSpec(name="folder_shortcut", handler="handle_folder_shortcut", matcher="_match_folder_shortcut"),
    CommandRouteSpec(name="quick_system", handler="handle_quick_system", matcher="_match_quick_system"),
    CommandRouteSpec(name="play_youtube", handler="play_youtube", matcher="_match_play_youtube"),
    CommandRouteSpec(name="social_media", handler="open_social_media", matcher="_match_social_media"),
    CommandRouteSpec(name="schedule", handler="schedule", patterns=(r"\b(university time table|schedule)\b",)),
    CommandRouteSpec(name="time", handler="tell_time", patterns=(r"\b(time|date|month)\b",)),
    CommandRouteSpec(name="volume", handler="volume_control", patterns=(r"\b(volume|mute|sound)\b",)),
    CommandRouteSpec(name="scroll", handler="scroll_navigate", patterns=(r"scroll up", r"scroll down", r"page up", r"page down", r"go back", r"go forward", r"go to top", r"go to bottom", r"scroll to top", r"scroll to bottom")),
    CommandRouteSpec(name="tab", handler="tab_management", matcher="_match_tab"),
    CommandRouteSpec(name="open_website", handler="open_website", matcher="_match_open_website"),
    CommandRouteSpec(name="open_app", handler="open_app", matcher="_match_open_app"),
    CommandRouteSpec(name="close_app", handler="close_app", matcher="_match_close_app"),
    CommandRouteSpec(name="browse", handler="_handle_browse", matcher="_match_browse"),
    CommandRouteSpec(name="system", handler="system_condition", matcher="_match_system"),
    CommandRouteSpec(name="weather", handler="get_weather", matcher="_match_weather"),
    CommandRouteSpec(name="wikipedia", handler="search_wikipedia", matcher="_match_wikipedia"),
    CommandRouteSpec(name="screenshot", handler="take_screenshot", matcher="_match_screenshot"),
    CommandRouteSpec(name="joke", handler="tell_joke", matcher="_match_joke"),
    CommandRouteSpec(name="exit", handler="_handle_exit", patterns=(r"^(exit|quit|exit meero|quit meero|goodbye|bye)$",)),
)
