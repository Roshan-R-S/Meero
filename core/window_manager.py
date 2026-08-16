"""Deterministic window management and quick system operations.

Provides safe local controls for window positioning, workspace layout,
screen locking, recycle bin management, and standard folder shortcuts.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _use_pyautogui_hotkey(*keys: str) -> bool:
    try:
        import pyautogui

        if hasattr(pyautogui, "hotkey"):
            pyautogui.hotkey(*keys)
            return True
    except Exception as exc:
        logger.debug("pyautogui hotkey %s failed: %s", keys, exc)
    return False


def minimize_all_windows() -> str:
    """Minimize all windows and show desktop."""
    if _use_pyautogui_hotkey("win", "d"):
        return "Showing desktop."
    return "Window control is unavailable."


def maximize_window() -> str:
    """Maximize the currently focused window."""
    if _use_pyautogui_hotkey("win", "up"):
        return "Maximized current window."
    return "Window control is unavailable."


def minimize_window() -> str:
    """Minimize the currently focused window."""
    if _use_pyautogui_hotkey("win", "down"):
        return "Minimized current window."
    return "Window control is unavailable."


def snap_window_left() -> str:
    """Snap active window to the left half of the screen."""
    if _use_pyautogui_hotkey("win", "left"):
        return "Snapped window to the left."
    return "Window control is unavailable."


def snap_window_right() -> str:
    """Snap active window to the right half of the screen."""
    if _use_pyautogui_hotkey("win", "right"):
        return "Snapped window to the right."
    return "Window control is unavailable."


def switch_window() -> str:
    """Switch to the next active application window."""
    if _use_pyautogui_hotkey("alt", "tab"):
        return "Switched window."
    return "Window control is unavailable."


def lock_screen() -> str:
    """Lock the Windows workstation securely."""
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.user32.LockWorkStation()
            return "Screen locked."
        except Exception as exc:
            logger.warning("Failed to lock workstation: %s", exc)
            return "Could not lock screen."
    return "Screen lock is only supported on Windows."


def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    if os.name == "nt":
        try:
            import ctypes

            # SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
            flags = 0x00000007
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            # S_OK is 0
            if result == 0:
                return "Recycle Bin emptied."
            return "Recycle Bin is already empty or operation cancelled."
        except Exception as exc:
            logger.warning("Failed to empty recycle bin: %s", exc)
            return "Could not empty recycle bin."
    return "Recycle bin operation is only supported on Windows."


_KNOWN_FOLDERS = {
    "downloads": Path.home() / "Downloads",
    "download": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "document": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "photos": Path.home() / "Pictures",
    "videos": Path.home() / "Videos",
    "music": Path.home() / "Music",
}


def open_folder_shortcut(folder_name: str) -> tuple[bool, str]:
    """Open a known user library folder shortcut."""
    clean_name = folder_name.lower().strip()
    target_path = None
    for key, path in _KNOWN_FOLDERS.items():
        if key in clean_name:
            target_path = path
            break

    if not target_path or not target_path.exists():
        return False, f"Could not find folder '{folder_name}'."

    try:
        if hasattr(os, "startfile"):
            os.startfile(str(target_path))
            return True, f"Opening {target_path.name} folder."
        import subprocess

        subprocess.Popen(["explorer", str(target_path)])
        return True, f"Opening {target_path.name} folder."
    except Exception as exc:
        logger.warning("Failed to open folder %s: %s", target_path, exc)
        return False, f"Could not open {target_path.name}."
