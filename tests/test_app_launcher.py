from unittest.mock import MagicMock, patch

import app_launcher


def test_launch_allowlist_fails_closed_in_local_desktop_mode(monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.APP_LAUNCH_ALLOWLIST", ())

    assert app_launcher.is_app_allowed("notepad") is False


def test_launch_allowlist_normalizes_names(monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.APP_LAUNCH_ALLOWLIST", (" Notepad ",))

    assert app_launcher.is_app_allowed("NOTEPAD") is True
    assert app_launcher.is_app_allowed("calculator") is False


@patch("app_launcher.subprocess.run")
def test_close_allowlist_fails_closed_in_local_desktop_mode(mock_run, monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.APP_CLOSE_ALLOWLIST", ())

    success, message = app_launcher.close_app_by_name("notepad")

    assert success is False
    assert "APP_CLOSE_ALLOWLIST" in message
    mock_run.assert_not_called()


@patch("app_launcher.subprocess.run")
def test_close_allowed_app_without_force(mock_run, monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.APP_CLOSE_ALLOWLIST", (" Notepad ",))
    monkeypatch.setattr("config.APP_FORCE_CLOSE_ALLOWLIST", ())
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    success, _message = app_launcher.close_app_by_name("NOTEPAD")

    assert success is True
    assert mock_run.call_args.args[0] == ["taskkill", "/im", "notepad.exe"]


@patch("app_launcher.subprocess.run")
def test_force_close_requires_close_permission(mock_run, monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.APP_CLOSE_ALLOWLIST", ("notepad",))
    monkeypatch.setattr("config.APP_FORCE_CLOSE_ALLOWLIST", ("spotify",))

    success, message = app_launcher.close_app_by_name("spotify")

    assert success is False
    assert "APP_CLOSE_ALLOWLIST" in message
    mock_run.assert_not_called()


@patch("app_launcher.subprocess.run")
def test_force_close_adds_force_flag_for_allowed_app(mock_run, monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.APP_CLOSE_ALLOWLIST", ("notepad",))
    monkeypatch.setattr("config.APP_FORCE_CLOSE_ALLOWLIST", (" Notepad ",))
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    success, _message = app_launcher.close_app_by_name("notepad")

    assert success is True
    assert mock_run.call_args.args[0] == ["taskkill", "/f", "/im", "notepad.exe"]
