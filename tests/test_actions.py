"""Unit tests for Actions class methods using ResponseCollector."""

import pytest
from unittest.mock import patch, MagicMock
from core.actions import Actions
from core.response_collector import ResponseCollector


@pytest.fixture
def actions():
    """Create an Actions instance with a ResponseCollector."""
    engine = ResponseCollector()
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
    @patch("core.actions.datetime")
    @patch("core.actions.time")
    def test_morning_greeting(self, mock_time, mock_dt, actions):
        act, engine = actions
        mock_dt.datetime.now.return_value.hour = 9
        mock_dt.datetime.today.return_value.strftime.return_value = "Monday"
        mock_time.strftime.return_value = "09:00 AM"
        act.wish_me()
        response = engine.get_response()
        assert "Good morning" in response

    @patch("core.actions.datetime")
    @patch("core.actions.time")
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

    @patch("core.actions.webbrowser")
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

    @patch("core.actions.start_file")
    def test_open_calculator(self, mock_startfile, actions, monkeypatch):
        monkeypatch.setattr("config.APP_LAUNCH_ALLOWLIST", ("calculator",))
        act, engine = actions
        act.process_command("open calculator")
        response = engine.get_response()
        assert "calculator" in response.lower()
        mock_startfile.assert_called_once()

    @patch("core.actions.start_file")
    def test_open_calculator_blocked_by_allowlist(self, mock_startfile, actions, monkeypatch):
        monkeypatch.setattr("config.APP_LAUNCH_ALLOWLIST", ("notepad",))
        act, engine = actions

        act.process_command("open calculator")

        response = engine.get_response().lower()
        assert "not allowed" in response
        mock_startfile.assert_not_called()

    @patch("core.actions.subprocess.run")
    def test_close_notepad(self, mock_run, actions, monkeypatch):
        monkeypatch.setattr("config.APP_CLOSE_ALLOWLIST", ("notepad",))
        mock_run.return_value.returncode = 0
        act, engine = actions
        act.process_command("close notepad")
        response = engine.get_response()
        assert "notepad" in response.lower()
        assert "should i continue" not in response.lower()
        mock_run.assert_called_once()

    @patch("core.actions.subprocess.run")
    def test_close_app_blocked_by_allowlist(self, mock_run, actions, monkeypatch):
        monkeypatch.setattr("config.APP_CLOSE_ALLOWLIST", ("notepad",))
        act, engine = actions

        act.process_command("close spotify", input_func=lambda: "yes")

        response = engine.get_response().lower()
        assert "not allowed" in response
        assert "app_close_allowlist" in response
        mock_run.assert_not_called()

    @patch("core.actions.webbrowser")
    def test_google_search(self, mock_browser, actions):
        act, engine = actions
        act.process_command("google search python tutorials", input_func=lambda: "None")
        response = engine.get_response()
        assert "searching" in response.lower()
        mock_browser.open.assert_called_once()
        # Verify URL encoding
        call_url = mock_browser.open.call_args[0][0]
        assert "google.com/search?q=" in call_url

    @patch("core.actions.webbrowser")
    @patch("core.actions.pyautogui")
    def test_open_new_tab_and_search(self, mock_gui, mock_browser, actions):
        act, engine = actions

        act.process_command("open new tab and search for amazon", input_func=lambda: "None")

        response = engine.get_response().lower()
        assert "searching for amazon" in response
        mock_browser.open.assert_called_once()
        mock_gui.hotkey.assert_not_called()
        assert "google.com/search?q=amazon" in mock_browser.open.call_args[0][0]

    def test_exit_command_calls_exit_func(self, actions):
        act, _ = actions
        exit_called = []
        act.process_command("exit", exit_func=lambda: exit_called.append(True))
        assert exit_called == [True]

    @patch("core.actions.webbrowser")
    def test_play_youtube(self, mock_browser, actions):
        act, engine = actions
        act.process_command("play despacito on youtube")
        response = engine.get_response()
        assert "playing" in response.lower()
        call_url = mock_browser.open.call_args[0][0]
        assert "youtube.com/results" in call_url


class TestVolumeControl:
    @patch("core.actions.pyautogui")
    def test_volume_up(self, mock_gui, actions):
        act, engine = actions
        act.process_command("volume up")
        response = engine.get_response().lower()
        assert "should i continue" not in response
        mock_gui.press.assert_called_with("volumeup")

    @patch("core.actions.pyautogui")
    def test_volume_mute(self, mock_gui, actions):
        act, engine = actions
        act.process_command("mute")
        response = engine.get_response().lower()
        assert "should i continue" not in response
        mock_gui.press.assert_called_with("volumemute")


class TestSensitiveCommandConfirmation:
    def test_delete_command_requires_confirmation(self, actions):
        act, engine = actions
        result = act.process_command("delete all files", input_func=lambda: "no")
        response = engine.get_response().lower()

        assert result == "action_cancelled"
        assert "delete data or change system settings" in response

    @patch("core.actions.app_launcher.find_and_open_app", return_value=(True, "Opening settings."))
    def test_settings_open_cancelled_without_yes(self, _mock_open, actions):
        act, engine = actions
        result = act.process_command("open settings", input_func=lambda: "no")
        response = engine.get_response().lower()

        assert result == "action_cancelled"
        assert "action cancelled" in response

    @patch("core.actions.app_launcher.find_and_open_app", return_value=(True, "Opening settings."))
    def test_settings_open_runs_when_confirmed(self, mock_open, actions):
        act, engine = actions
        result = act.process_command("open settings", input_func=lambda: "yes")
        response = engine.get_response().lower()

        assert result is None
        assert "opening settings" in response
        mock_open.assert_called_once()


class TestMediaControl:
    @patch("core.media_control._send_media_key_windows", return_value=True)
    def test_pause_command(self, mock_send, actions):
        act, engine = actions
        act.process_command("pause")
        response = engine.get_response().lower()
        assert "toggled media playback" in response
        mock_send.assert_called_once()

    @patch("core.media_control._send_media_key_windows", return_value=True)
    def test_next_track_command(self, mock_send, actions):
        act, engine = actions
        act.process_command("next track")
        response = engine.get_response().lower()
        assert "next track" in response
        mock_send.assert_called_once()

    @patch("core.media_control._send_media_key_windows", return_value=True)
    def test_previous_track_command(self, mock_send, actions):
        act, engine = actions
        act.process_command("previous track")
        response = engine.get_response().lower()
        assert "previous track" in response
        mock_send.assert_called_once()


class TestReminderCommand:
    def test_schedule_reminder(self, actions, tmp_path, monkeypatch):
        act, engine = actions
        from core.reminder_service import ReminderService
        test_srv = ReminderService(db_path=tmp_path / "test_rem.db")
        monkeypatch.setattr("core.reminder_service.get_reminder_service", lambda: test_srv)

        act.process_command("remind me in 10 minutes to drink water")
        response = engine.get_response().lower()
        assert "remind you to drink water in 10 minutes" in response
        assert len(test_srv.list_pending()) == 1

    def test_cancel_reminder(self, actions, tmp_path, monkeypatch):
        act, engine = actions
        from core.reminder_service import ReminderService
        test_srv = ReminderService(db_path=tmp_path / "test_rem.db")
        test_srv.schedule("drink water", 600)
        monkeypatch.setattr("core.reminder_service.get_reminder_service", lambda: test_srv)

        act.process_command("cancel reminder")
        response = engine.get_response().lower()
        assert "cancelled reminder: drink water" in response
        assert len(test_srv.list_pending()) == 0


class TestWindowManagement:
    @patch("core.window_manager._use_pyautogui_hotkey", return_value=True)
    def test_minimize_all(self, mock_hotkey, actions):
        act, engine = actions
        act.process_command("minimize all")
        response = engine.get_response().lower()
        assert "showing desktop" in response
        mock_hotkey.assert_called_with("win", "d")

    @patch("core.window_manager._use_pyautogui_hotkey", return_value=True)
    def test_snap_window_left(self, mock_hotkey, actions):
        act, engine = actions
        act.process_command("snap window left")
        response = engine.get_response().lower()
        assert "snapped window to the left" in response
        mock_hotkey.assert_called_with("win", "left")


class TestFolderShortcuts:
    @patch("core.window_manager.open_folder_shortcut", return_value=(True, "Opening Downloads folder."))
    def test_open_downloads(self, mock_open_folder, actions):
        act, engine = actions
        act.process_command("open downloads")
        response = engine.get_response().lower()
        assert "opening downloads folder" in response
        mock_open_folder.assert_called_once()


class TestQuickSystem:
    @patch("core.window_manager.lock_screen", return_value="Screen locked.")
    def test_lock_screen(self, mock_lock, actions):
        act, engine = actions
        act.process_command("lock screen")
        response = engine.get_response().lower()
        assert "screen locked" in response
        mock_lock.assert_called_once()

    @patch("core.window_manager.empty_recycle_bin", return_value="Recycle Bin emptied.")
    def test_empty_recycle_bin_with_confirmation(self, mock_empty, actions):
        act, engine = actions
        result = act.process_command("empty recycle bin", input_func=lambda: "yes")
        response = engine.get_response().lower()
        assert result is None
        assert "recycle bin emptied" in response
        mock_empty.assert_called_once()

