"""
Dynamic App Launcher for Windows.
Finds and opens any installed application by name using multiple strategies:
1. shutil.which() — finds executables on PATH
2. Windows Start Menu shortcuts (.lnk files)
3. Common install locations
"""

import os
import glob
import shutil
import subprocess
import logging

import config

logger = logging.getLogger(__name__)

# Cache Start Menu shortcuts on first use
_start_menu_cache = None


def _normalized_allowlist():
    return {
        item.strip().lower()
        for item in getattr(config, "APP_LAUNCH_ALLOWLIST", ())
        if item and item.strip()
    }


def is_app_allowed(app_name):
    """Return whether app launch/close is allowed by the allowlist."""
    allowed = _normalized_allowlist()
    
    if getattr(config, "LOCAL_DESKTOP_MODE", False):
        if not allowed:
            # If in local desktop mode and allowlist is empty, block all app launches
            return False
            
    if not allowed:
        return True
    return app_name.lower().strip() in allowed


def _blocked_message(app_name, action):
    return (
        False,
        f"{action.capitalize()} {app_name} is not allowed by APP_LAUNCH_ALLOWLIST.",
    )


def _build_start_menu_cache():
    """Scan Start Menu folders for .lnk shortcut files."""
    global _start_menu_cache
    if _start_menu_cache is not None:
        return _start_menu_cache

    _start_menu_cache = {}
    search_dirs = [
        os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                     "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("APPDATA", ""),
                     "Microsoft", "Windows", "Start Menu", "Programs"),
    ]

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        for lnk_file in glob.glob(os.path.join(search_dir, "**", "*.lnk"), recursive=True):
            # Use the shortcut filename (minus .lnk) as the app name
            name = os.path.splitext(os.path.basename(lnk_file))[0].lower()
            _start_menu_cache[name] = lnk_file

    logger.info("Start Menu cache built: %d shortcuts found", len(_start_menu_cache))
    return _start_menu_cache


def _find_in_start_menu(app_name):
    """Find the best matching .lnk shortcut for the given app name."""
    cache = _build_start_menu_cache()
    app_lower = app_name.lower().strip()

    # 1. Exact match
    if app_lower in cache:
        return cache[app_lower]

    # 2. Partial match — app name is contained in shortcut name
    matches = [(name, path) for name, path in cache.items() if app_lower in name]
    if matches:
        # Prefer shortest name (most specific match)
        matches.sort(key=lambda x: len(x[0]))
        return matches[0][1]

    return None


def find_and_open_app(app_name):
    """
    Try to open an application by name. Returns (success, message).
    
    Strategy:
    1. Check PATH using shutil.which()
    2. Search Windows Start Menu shortcuts
    3. Try direct os.startfile() as last resort
    """
    app_lower = app_name.lower().strip()

    if not app_lower:
        return False, "I didn't catch the application name."

    if not is_app_allowed(app_lower):
        return _blocked_message(app_name, "opening")

    # Strategy 1: Check PATH (works for CLI tools, browsers, etc.)
    exe_path = shutil.which(app_lower)
    if exe_path:
        logger.info("Found '%s' on PATH: %s", app_name, exe_path)
        subprocess.Popen([exe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"Opening {app_name}."

    # Strategy 2: Search Start Menu shortcuts
    lnk_path = _find_in_start_menu(app_lower)
    if lnk_path:
        logger.info("Found '%s' in Start Menu: %s", app_name, lnk_path)
        os.startfile(lnk_path)
        return True, f"Opening {app_name}."

    # Strategy 3: Try common variations
    common_exes = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "word": "WINWORD.EXE",
        "excel": "EXCEL.EXE",
        "powerpoint": "POWERPNT.EXE",
        "outlook": "OUTLOOK.EXE", 
        "teams": "ms-teams.exe",
        "spotify": "Spotify.exe",
        "discord": "Discord.exe",
        "vlc": "vlc.exe",
        "obs": "obs64.exe",
        "terminal": "wt.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "file explorer": "explorer.exe",
        "explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "settings": "ms-settings:",
        "store": "ms-windows-store:",
        "snipping tool": "SnippingTool.exe",
    }

    if app_lower in common_exes:
        target = common_exes[app_lower]
        logger.info("Using common exe mapping: '%s' -> '%s'", app_name, target)
        try:
            if target.endswith(":"):
                # URI scheme (ms-settings:, etc.)
                os.startfile(target)
            else:
                exe = shutil.which(target)
                if exe:
                    subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.startfile(target)
            return True, f"Opening {app_name}."
        except Exception:
            logger.exception("Failed to open '%s' via common mapping", app_name)

    return False, f"I couldn't find an application called {app_name}."


def close_app_by_name(app_name):
    """
    Try to close an application by name using taskkill.
    Returns (success, message).
    """
    app_lower = app_name.lower().strip()

    if getattr(config, "APP_CLOSE_ALLOWLIST", None) and app_lower not in config.APP_CLOSE_ALLOWLIST:
        return False, f"Closing {app_name} is blocked by your safety configuration."

    # Map common names to process names
    process_map = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "word": "WINWORD.EXE",
        "excel": "EXCEL.EXE",
        "powerpoint": "POWERPNT.EXE",
        "outlook": "OUTLOOK.EXE",
        "spotify": "Spotify.exe",
        "discord": "Discord.exe",
        "vlc": "vlc.exe",
        "obs": "obs64.exe",
        "notepad": "notepad.exe",
        "calculator": "CalculatorApp.exe",
        "paint": "mspaint.exe",
        "teams": "ms-teams.exe",
        "terminal": "WindowsTerminal.exe",
        "vscode": "Code.exe",
        "code": "Code.exe",
        "visual studio code": "Code.exe",
    }

    process_name = process_map.get(app_lower)
    
    if not process_name:
        # Try appending .exe and using it directly
        process_name = app_lower if app_lower.endswith(".exe") else f"{app_lower}.exe"

    force_close = getattr(config, "APP_FORCE_CLOSE_ALLOWLIST", None) and app_lower in config.APP_FORCE_CLOSE_ALLOWLIST
    
    taskkill_args = ["taskkill", "/im", process_name]
    if force_close:
        taskkill_args.insert(1, "/f")

    result = subprocess.run(
        taskkill_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode == 0:
        return True, f"Closed {app_name}."
    else:
        logger.warning("taskkill failed for '%s': %s", process_name, result.stderr.strip())
        return False, f"I couldn't close {app_name}. It may not be running."
