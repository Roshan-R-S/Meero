"""Unit tests for Actions class methods using MockSpeechEngine."""

import pytest
from unittest.mock import patch, MagicMock
from actions import Actions
from mock_engine import MockSpeechEngine


@pytest.fixture
def actions():
    """Create an Actions instance with a MockSpeechEngine."""
    engine = MockSpeechEngine()
    return Actions(engine), engine


class TestCalDay:
    def test_returns_weekday_name(self, actions):
        act, _ = actions
        day = act.cal_day()
        assert day in [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]


class TestWishMe:
    @patch("actions.datetime")
    @patch("actions.time")
    def test_morning_greeting(self, mock_time, mock_dt, actions):
        act, engine = actions
        mock_dt.datetime.now.return_value.hour = 9
        mock_dt.datetime.today.return_value.strftime.return_value = "Monday"
        mock_time.strftime.return_value = "09:00 AM"
        act.wish_me()
        response = engine.get_response()
        assert "Good morning" in response

    @patch("actions.datetime")
    @patch("actions.time")
    def test_evening_greeting(self, mock_time, mock_dt, actions):
        act, engine = actions
        mock_dt.datetime.now.return_value.hour = 20
        mock_dt.datetime.today.return_value.strftime.return_value = "Friday"
        mock_time.strftime.return_value = "08:00 PM"
        act.wish_me()
        response = engine.get_response()
        assert "Good evening" in response


class TestProcessCommand:
    def test_empty_query_returns_none(self, actions):
        act, _ = actions
        result = act.process_command("")
        assert result is None

    def test_none_query_returns_none(self, actions):
        act, _ = actions
        result = act.process_command("None")
        assert result is None

    def test_unknown_command_returns_fallback(self, actions):
        act, _ = actions
        result = act.process_command("what is quantum physics")
        assert result == "neural_net_fallback"

    @patch("actions.webbrowser")
    def test_open_youtube(self, mock_browser, actions):
        act, engine = actions
        act.process_command("open youtube")
        response = engine.get_response()
        assert "youtube" in response.lower()
        mock_browser.open.assert_called_once()

    def test_joke_command(self, actions):
        act, engine = actions
        act.process_command("tell me a joke")
        response = engine.get_response()
        assert len(response) > 0  # Joke should produce some text

    def test_time_command(self, actions):
        act, engine = actions
        act.process_command("what time is it")
        response = engine.get_response()
        assert "time is" in response.lower()

    def test_date_command(self, actions):
        act, engine = actions
        act.process_command("what is the date")
        response = engine.get_response()
        assert "date is" in response.lower()

    @patch("actions.os.startfile")
    def test_open_calculator(self, mock_startfile, actions):
        act, engine = actions
        act.process_command("open calculator")
        response = engine.get_response()
        assert "calculator" in response.lower()
        mock_startfile.assert_called_once()

    @patch("actions.subprocess.run")
    def test_close_notepad(self, mock_run, actions):
        act, engine = actions
        act.process_command("close notepad")
        response = engine.get_response()
        assert "notepad" in response.lower()
        mock_run.assert_called_once()

    @patch("actions.webbrowser")
    def test_google_search(self, mock_browser, actions):
        act, engine = actions
        act.process_command("google search python tutorials", input_func=lambda: "None")
        response = engine.get_response()
        assert "searching" in response.lower()
        mock_browser.open.assert_called_once()
        # Verify URL encoding
        call_url = mock_browser.open.call_args[0][0]
        assert "google.com/search?q=" in call_url

    def test_exit_command_calls_exit_func(self, actions):
        act, _ = actions
        exit_called = []
        act.process_command("exit", exit_func=lambda: exit_called.append(True))
        assert exit_called == [True]

    @patch("actions.webbrowser")
    def test_play_youtube(self, mock_browser, actions):
        act, engine = actions
        act.process_command("play despacito on youtube")
        response = engine.get_response()
        assert "playing" in response.lower()
        call_url = mock_browser.open.call_args[0][0]
        assert "youtube.com/results" in call_url


class TestVolumeControl:
    @patch("actions.pyautogui")
    def test_volume_up(self, mock_gui, actions):
        act, engine = actions
        act.process_command("volume up")
        mock_gui.press.assert_called_with("volumeup")

    @patch("actions.pyautogui")
    def test_volume_mute(self, mock_gui, actions):
        act, engine = actions
        act.process_command("mute")
        mock_gui.press.assert_called_with("volumemute")
