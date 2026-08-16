"""Deterministic local media playback controls.

Uses Windows keybd_event (or pyautogui fallback) to send standard multimedia
virtual key strokes for play/pause, next track, previous track, and stop.
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

# Windows Virtual Key Codes for Media Controls
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_media_key_windows(vk_code: int) -> bool:
    """Send a multimedia key event using Windows Win32 API via ctypes."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return True
    except Exception as exc:
        logger.warning("Failed to dispatch media key via ctypes: %s", exc)
        return False


def _send_media_key_pyautogui(action: str) -> bool:
    """Fallback to pyautogui if available."""
    try:
        import pyautogui

        if hasattr(pyautogui, "press"):
            pyautogui.press(action)
            return True
    except Exception:
        pass
    return False


def play_pause_media() -> str:
    """Toggle play/pause state for the active media player."""
    if _send_media_key_windows(VK_MEDIA_PLAY_PAUSE) or _send_media_key_pyautogui("playpause"):
        return "Toggled media playback."
    return "Media control is not supported on this system."


def next_track() -> str:
    """Skip to the next media track."""
    if _send_media_key_windows(VK_MEDIA_NEXT_TRACK) or _send_media_key_pyautogui("nexttrack"):
        return "Skipped to the next track."
    return "Media control is not supported on this system."


def previous_track() -> str:
    """Return to the previous media track."""
    if _send_media_key_windows(VK_MEDIA_PREV_TRACK) or _send_media_key_pyautogui("prevtrack"):
        return "Returning to the previous track."
    return "Media control is not supported on this system."


def stop_media() -> str:
    """Stop active media playback."""
    if _send_media_key_windows(VK_MEDIA_STOP) or _send_media_key_pyautogui("stop"):
        return "Stopped media playback."
    return "Media control is not supported on this system."
