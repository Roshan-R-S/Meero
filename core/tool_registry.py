"""Registry and execution dispatcher for local LLM tool calling."""

from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="open_app",
        description="Launch a desktop application by name (e.g. notepad, calculator, vscode, spotify).",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The name of the application."}},
            "required": ["name"],
        },
    ),
    ToolSpec(
        name="close_app",
        description="Close or terminate a running application by name.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The name of the application to close."}},
            "required": ["name"],
        },
    ),
    ToolSpec(
        name="open_website",
        description="Open a website in the default browser.",
        parameters={
            "type": "object",
            "properties": {"site": {"type": "string", "description": "Website name or domain (e.g. github, youtube, reddit)."}},
            "required": ["site"],
        },
    ),
    ToolSpec(
        name="set_volume",
        description="Adjust system volume level.",
        parameters={
            "type": "object",
            "properties": {"action": {"type": "string", "enum": ["up", "down", "mute"], "description": "Volume action to perform."}},
            "required": ["action"],
        },
    ),
    ToolSpec(
        name="media_control",
        description="Control background media playback (play, pause, next track, previous track, stop).",
        parameters={
            "type": "object",
            "properties": {"action": {"type": "string", "enum": ["play_pause", "next", "previous", "stop"]}},
            "required": ["action"],
        },
    ),
    ToolSpec(
        name="schedule_reminder",
        description="Schedule a reminder or timer for a specific duration in seconds.",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "What to remind the user about."},
                "delay_seconds": {"type": "number", "description": "Seconds from now when the reminder is due."},
            },
            "required": ["message", "delay_seconds"],
        },
    ),
    ToolSpec(
        name="window_action",
        description="Manage workspace window layouts and positioning.",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["minimize_all", "maximize", "minimize", "snap_left", "snap_right", "switch"],
                }
            },
            "required": ["action"],
        },
    ),
    ToolSpec(
        name="take_screenshot",
        description="Capture and save a full screen screenshot.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="lock_screen",
        description="Lock the computer screen workstation.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="tell_time",
        description="Get current time, date, or month.",
        parameters={
            "type": "object",
            "properties": {"query_type": {"type": "string", "enum": ["time", "date", "month"]}},
            "required": ["query_type"],
        },
    ),
    ToolSpec(
        name="tell_joke",
        description="Tell a programmer or general humor joke.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="system_condition",
        description="Check current CPU usage and battery status.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="search_wikipedia",
        description="Search Wikipedia for summary information on a topic.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Topic to search for."}},
            "required": ["query"],
        },
    ),
]


def format_tools_for_prompt() -> str:
    """Format available tool specifications for prompt inclusion."""
    lines = ["Available tools:"]
    for tool in TOOL_SPECS:
        params_str = ", ".join(
            f"{k}: {v.get('type', 'any')}" for k, v in tool.parameters.get("properties", {}).items()
        )
        lines.append(f"- {tool.name}({params_str}): {tool.description}")
    return "\n".join(lines)


def execute_tool(tool_name: str, args: dict[str, Any], actions: Any) -> str:
    """
    Execute a tool call using the Actions instance or underlying services.
    Returns the action's spoken result text.
    """
    # Create a temporary collector if actions doesn't have a direct string return
    from core.response_collector import ResponseCollector
    collector = ResponseCollector()
    original_speak = getattr(actions, "speak", None)
    
    # Intercept speech output to capture response
    actions.speak = collector.speak
    try:
        if tool_name == "open_app":
            app_name = args.get("name", "")
            actions.open_app(f"open {app_name}")
        elif tool_name == "close_app":
            app_name = args.get("name", "")
            actions.close_app(f"close {app_name}")
        elif tool_name == "open_website":
            site = args.get("site", "")
            actions.open_website(f"open {site}")
        elif tool_name == "set_volume":
            action = args.get("action", "up")
            actions.volume_control(f"volume {action}")
        elif tool_name == "media_control":
            action = args.get("action", "play_pause")
            actions.handle_media_control(action)
        elif tool_name == "schedule_reminder":
            msg = args.get("message", "Reminder")
            delay = float(args.get("delay_seconds", 60))
            from core.reminder_service import get_reminder_service
            srv = get_reminder_service()
            srv.schedule(msg, delay)
            time_desc = f"{int(delay)} seconds" if delay < 60 else f"{int(delay // 60)} minutes"
            actions.speak(f"Scheduled reminder: {msg} in {time_desc}.")
        elif tool_name == "window_action":
            action = args.get("action", "minimize_all")
            actions.handle_window_management(action)
        elif tool_name == "take_screenshot":
            actions.take_screenshot()
        elif tool_name == "lock_screen":
            actions.handle_quick_system("lock screen")
        elif tool_name == "tell_time":
            q_type = args.get("query_type", "time")
            actions.tell_time(q_type)
        elif tool_name == "tell_joke":
            actions.tell_joke()
        elif tool_name == "system_condition":
            actions.system_condition()
        elif tool_name == "search_wikipedia":
            q = args.get("query", "")
            actions.search_wikipedia(f"search wikipedia for {q}")
        else:
            return f"Unknown tool: {tool_name}"
        
        return collector.get_response() or f"Executed {tool_name}."
    finally:
        if original_speak is not None:
            actions.speak = original_speak
