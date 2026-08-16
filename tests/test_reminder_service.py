"""Unit tests for the local-first ReminderService and parser."""

import time
import pytest
from pathlib import Path
from core.reminder_service import ReminderService, parse_reminder_query


@pytest.fixture
def temp_reminder_service(tmp_path: Path):
    db_path = tmp_path / "test_reminders.db"
    service = ReminderService(db_path=db_path)
    yield service
    service.stop_daemon()


def test_parse_reminder_query():
    # "remind me in 10 minutes to drink water"
    res = parse_reminder_query("remind me in 10 minutes to drink water")
    assert res is not None
    msg, delay = res
    assert msg == "drink water"
    assert delay == 600

    # "remind me in 5 seconds to test"
    res = parse_reminder_query("remind me in 5 seconds to test")
    assert res is not None
    msg, delay = res
    assert msg == "test"
    assert delay == 5

    # "to call mom in 2 hours"
    res = parse_reminder_query("remind me to call mom in 2 hours")
    assert res is not None
    msg, delay = res
    assert msg == "call mom"
    assert delay == 7200

    # "set a timer for 15 minutes"
    res = parse_reminder_query("set a timer for 15 minutes")
    assert res is not None
    msg, delay = res
    assert "Timer for 15 minutes" in msg
    assert delay == 900

    # Invalid query
    res = parse_reminder_query("what is the weather today")
    assert res is None


def test_schedule_and_list(temp_reminder_service: ReminderService):
    rem = temp_reminder_service.schedule("Buy milk", 120)
    assert rem.id == 1
    assert rem.message == "Buy milk"
    assert rem.status == "pending"

    pending = temp_reminder_service.list_pending()
    assert len(pending) == 1
    assert pending[0].message == "Buy milk"


def test_cancel_reminder(temp_reminder_service: ReminderService):
    rem = temp_reminder_service.schedule("Call John", 60)
    assert temp_reminder_service.cancel(rem.id) is True
    assert len(temp_reminder_service.list_pending()) == 0

    # Cancel non-existent
    assert temp_reminder_service.cancel(999) is False


def test_cancel_latest(temp_reminder_service: ReminderService):
    temp_reminder_service.schedule("First task", 100)
    temp_reminder_service.schedule("Second task", 200)

    cancelled = temp_reminder_service.cancel_latest()
    assert cancelled is not None
    assert cancelled.message == "Second task"
    assert len(temp_reminder_service.list_pending()) == 1


def test_trigger_and_callback(temp_reminder_service: ReminderService):
    triggered = []

    def on_reminder(rem):
        triggered.append(rem)

    temp_reminder_service._on_reminder_callbacks.append(on_reminder)

    # Schedule a reminder with tiny delay
    temp_reminder_service.schedule("Immediate task", 0.05)
    time.sleep(0.1)

    # Check and trigger
    temp_reminder_service._check_and_trigger()
    assert len(triggered) == 1
    assert triggered[0].message == "Immediate task"
    assert len(temp_reminder_service.list_pending()) == 0
