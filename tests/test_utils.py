import datetime

from meldingen.schemas.types import DaysType
from meldingen.utils import days_passed_since, format_safe


def test_format_safe_replaces_known_keys_and_keeps_unknown_keys() -> None:
    template = "Hello {name}, ticket {ticket_id}, status {status}."
    mapping = {"name": "Jan", "ticket_id": 42}

    result = format_safe(template, mapping)

    assert result == "Hello Jan, ticket 42, status {status}."


def test_days_passed_since_calendar_days_uses_half_open_interval() -> None:
    start = datetime.date(2026, 9, 24)
    end = datetime.date(2026, 10, 1)

    days = days_passed_since(start, end, DaysType.calendar_days)

    assert days == 7


def test_days_passed_since_working_days_excludes_weekends() -> None:
    start = datetime.date(2026, 9, 26)  # Saturday
    end = datetime.date(2026, 10, 1)  # Thursday

    days = days_passed_since(start, end, DaysType.working_days)

    assert days == 3


def test_days_passed_since_same_start_and_end_is_zero() -> None:
    day = datetime.date(2026, 10, 1)

    calendar_days = days_passed_since(
        day,
        day,
        DaysType.calendar_days,
    )
    working_days = days_passed_since(
        day,
        day,
        DaysType.working_days,
    )

    assert calendar_days == 0
    assert working_days == 0


def test_days_passed_since_uses_current_utc_date_when_end_is_none(monkeypatch) -> None:
    class FrozenDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 1, tzinfo=tz)

    from meldingen import utils

    monkeypatch.setattr(utils.datetime, "datetime", FrozenDateTime)

    start = datetime.date(2026, 9, 29)

    calendar_days = days_passed_since(
        start,
        None,
        DaysType.calendar_days,
    )
    working_days = days_passed_since(
        start,
        None,
        DaysType.working_days,
    )

    assert calendar_days == 2
    assert working_days == 2
