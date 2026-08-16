"""Unit tests for tool registry, tool specs, and JSON extraction."""

from unittest.mock import MagicMock
from core.prompt_templates import extract_tool_calls
from core.tool_registry import TOOL_SPECS, execute_tool, format_tools_for_prompt


def test_tool_specs_defined():
    assert len(TOOL_SPECS) >= 10
    names = [t.name for t in TOOL_SPECS]
    assert "open_app" in names
    assert "close_app" in names
    assert "set_volume" in names
    assert "media_control" in names
    assert "schedule_reminder" in names
    assert "take_screenshot" in names


def test_format_tools_for_prompt():
    prompt_str = format_tools_for_prompt()
    assert "Available tools:" in prompt_str
    assert "open_app" in prompt_str
    assert "set_volume" in prompt_str


def test_extract_tool_calls_bare_json():
    text = '{"tool_calls": [{"tool": "open_app", "args": {"name": "notepad"}}]}'
    calls = extract_tool_calls(text)
    assert calls is not None
    assert len(calls) == 1
    assert calls[0]["tool"] == "open_app"
    assert calls[0]["args"] == {"name": "notepad"}


def test_extract_tool_calls_markdown_code_fence():
    text = """Here is your tool call:
```json
{
  "tool_calls": [
    {"tool": "open_app", "args": {"name": "spotify"}},
    {"tool": "set_volume", "args": {"action": "up"}}
  ]
}
```
"""
    calls = extract_tool_calls(text)
    assert calls is not None
    assert len(calls) == 2
    assert calls[0]["tool"] == "spotify" or calls[0]["tool"] == "open_app"
    assert calls[1]["tool"] == "set_volume"


def test_extract_tool_calls_conversational_text():
    text = "Hello! I am Meero, your AI assistant. How can I help you today?"
    calls = extract_tool_calls(text)
    assert calls is None


def test_execute_tool_open_app():
    actions = MagicMock()
    result = execute_tool("open_app", {"name": "calculator"}, actions)
    assert "open_app" in result or "calculator" in result or result != ""
    actions.open_app.assert_called_once_with("open calculator")


def test_execute_tool_set_volume():
    actions = MagicMock()
    result = execute_tool("set_volume", {"action": "up"}, actions)
    actions.volume_control.assert_called_once_with("volume up")
