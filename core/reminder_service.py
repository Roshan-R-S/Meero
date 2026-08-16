"""Local-first reminder and timer service with SQLite persistence.

Manages timed reminders and timers completely locally with background scheduling
and Windows notification toasts.
"""

from __future__ import annotations

import dataclasses
import datetime
import logging
import os
import re
import sqlite3
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/reminders.db")


@dataclasses.dataclass(frozen=True)
class Reminder:
    id: int
    message: str
    due_at: float
    created_at: float
    status: str  # "pending", "completed", "cancelled"

    @property
    def due_datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.due_at)


class ReminderService:
    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._lock = threading.Lock()
        self._daemon_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_reminder_callbacks: list[Callable[[Reminder], None]] = []
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    due_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )
            conn.commit()

    def schedule(self, message: str, delay_seconds: float) -> Reminder:
        """Schedule a new reminder."""
        if delay_seconds <= 0:
            raise ValueError("Delay must be a positive number of seconds.")
        now = time.time()
        due_at = now + delay_seconds
        clean_message = message.strip() or "Reminder"

        with self._lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (message, due_at, created_at, status) VALUES (?, ?, ?, 'pending')",
                (clean_message, due_at, now),
            )
            reminder_id = cursor.lastrowid
            conn.commit()

        reminder = Reminder(
            id=reminder_id,
            message=clean_message,
            due_at=due_at,
            created_at=now,
            status="pending",
        )
        logger.info("Scheduled reminder #%d: '%s' in %.1fs", reminder_id, clean_message, delay_seconds)
        return reminder

    def list_pending(self) -> list[Reminder]:
        """List all currently pending reminders."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, message, due_at, created_at, status FROM reminders WHERE status = 'pending' ORDER BY due_at ASC"
            )
            rows = cursor.fetchall()
            return [
                Reminder(id=r[0], message=r[1], due_at=r[2], created_at=r[3], status=r[4])
                for r in rows
            ]

    def cancel(self, reminder_id: int) -> bool:
        """Cancel a pending reminder by ID."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reminders SET status = 'cancelled' WHERE id = ? AND status = 'pending'",
                (reminder_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def cancel_latest(self) -> Optional[Reminder]:
        """Cancel the most recently scheduled pending reminder."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, message, due_at, created_at, status FROM reminders WHERE status = 'pending' ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute("UPDATE reminders SET status = 'cancelled' WHERE id = ?", (row[0],))
            conn.commit()
            return Reminder(id=row[0], message=row[1], due_at=row[2], created_at=row[3], status="cancelled")

    def _mark_completed(self, reminder_id: int) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE reminders SET status = 'completed' WHERE id = ?",
                (reminder_id,),
            )
            conn.commit()

    def _check_and_trigger(self) -> None:
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, message, due_at, created_at, status FROM reminders WHERE status = 'pending' AND due_at <= ?",
                (now,),
            )
            due_rows = cursor.fetchall()

        for r in due_rows:
            reminder = Reminder(id=r[0], message=r[1], due_at=r[2], created_at=r[3], status="completed")
            self._mark_completed(reminder.id)
            self._trigger_notification(reminder)

    def _trigger_notification(self, reminder: Reminder) -> None:
        logger.info("Reminder triggered: %s", reminder.message)
        # 1. Fire OS Toast on Windows
        if os.name == "nt":
            self._show_windows_notification(reminder.message)
        # 2. Call any registered callback
        for cb in list(self._on_reminder_callbacks):
            try:
                cb(reminder)
            except Exception as exc:
                logger.warning("Error in reminder callback: %s", exc)

    @staticmethod
    def _show_windows_notification(message: str) -> None:
        """Display a native Windows notification toast."""
        escaped_msg = message.replace("'", "''").replace('"', '`"')
        powershell_script = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
            "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            "$textNodes = $template.GetElementsByTagName('text'); "
            "$textNodes.Item(0).AppendChild($template.CreateTextNode('Meero Reminder')) > $null; "
            f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{escaped_msg}')) > $null; "
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Meero Assistant').Show($toast);"
        )
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", powershell_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            logger.debug("Failed to spawn Windows toast notification: %s", exc)

    def start_daemon(self) -> None:
        """Start the background reminder monitoring thread."""
        if self._daemon_thread and self._daemon_thread.is_alive():
            return
        self._stop_event.clear()
        self._daemon_thread = threading.Thread(target=self._run_daemon, daemon=True, name="ReminderDaemon")
        self._daemon_thread.start()
        logger.info("Reminder service background daemon started.")

    def stop_daemon(self) -> None:
        """Stop the background reminder monitoring thread."""
        self._stop_event.set()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=2.0)
        logger.info("Reminder service background daemon stopped.")

    def _run_daemon(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_and_trigger()
            except Exception as exc:
                logger.error("Error during reminder check: %s", exc)
            self._stop_event.wait(1.0)


# Global singleton instance
_default_reminder_service: Optional[ReminderService] = None


def get_reminder_service() -> ReminderService:
    global _default_reminder_service
    if _default_reminder_service is None:
        _default_reminder_service = ReminderService()
    return _default_reminder_service


def parse_reminder_query(query: str) -> Optional[tuple[str, float]]:
    """
    Parse duration and message from natural language reminder queries.
    Returns (reminder_message, delay_seconds) or None if unparseable.
    
    Supports formats:
      - "remind me in 10 minutes to drink water"
      - "remind me in 5 seconds to test"
      - "remind me to check oven in 1 hour"
      - "set a timer for 15 minutes"
      - "timer for 30 seconds"
    """
    q = query.lower().strip()

    # Match duration units (hours, minutes, seconds)
    # 1. "in X hours/minutes/seconds to [action]"
    pattern_in_to = re.search(
        r"\bin\s+(\d+(?:\.\d+)?)\s+(hour|hr|minute|min|second|sec)s?\s+(?:to\s+|for\s+)?(.+)$",
        q,
    )
    if pattern_in_to:
        amount = float(pattern_in_to.group(1))
        unit = pattern_in_to.group(2)
        message = pattern_in_to.group(3).strip()
        multiplier = {"hour": 3600, "hr": 3600, "minute": 60, "min": 60, "second": 1, "sec": 1}[unit]
        return message, amount * multiplier

    # 2. "to [action] in X hours/minutes/seconds"
    pattern_to_in = re.search(
        r"(?:remind me\s+)?to\s+(.+?)\s+in\s+(\d+(?:\.\d+)?)\s+(hour|hr|minute|min|second|sec)s?$",
        q,
    )
    if pattern_to_in:
        message = pattern_to_in.group(1).strip()
        amount = float(pattern_to_in.group(2))
        unit = pattern_to_in.group(3)
        multiplier = {"hour": 3600, "hr": 3600, "minute": 60, "min": 60, "second": 1, "sec": 1}[unit]
        return message, amount * multiplier

    # 3. "set a timer for X hours/minutes/seconds" or "timer for X minutes"
    pattern_timer = re.search(
        r"\b(?:set\s+(?:a\s+)?)?timer\s+(?:for\s+)?(\d+(?:\.\d+)?)\s+(hour|hr|minute|min|second|sec)s?(?:\s+(?:for|to)\s+(.+))?$",
        q,
    )
    if pattern_timer:
        amount = float(pattern_timer.group(1))
        unit = pattern_timer.group(2)
        label = pattern_timer.group(3)
        multiplier = {"hour": 3600, "hr": 3600, "minute": 60, "min": 60, "second": 1, "sec": 1}[unit]
        duration_desc = f"{int(amount) if amount.is_integer() else amount} {unit}{'s' if amount != 1 else ''}"
        message = f"Timer for {duration_desc}" + (f": {label.strip()}" if label else "")
        return message, amount * multiplier

    return None
