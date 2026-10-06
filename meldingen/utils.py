import datetime
from typing import Any

from meldingen.schemas.types import DaysType


class SafeTemplateDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def format_safe(template: str, mapping: dict[str, Any]) -> str:
    return template.format_map(SafeTemplateDict(mapping))

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


def utc_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime.datetime:
    return datetime.datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        microsecond,
        tzinfo=datetime.UTC,
    )



def days_passed_since(
    date: datetime.date,
    date2: datetime.date | None,
    days_type: DaysType = DaysType.calendar_days,
) -> int:
    """Count days in the half-open interval [date, date2) according to the specified day type.

    The start date is included. The end date is excluded.
    If date2 is None, the current UTC date is used.

    Holidays are never taken into account.
    """

    if date2 is None:
        date2 = datetime.datetime.now(datetime.UTC).date()

    # Calendar days, all days are counted
    if days_type == DaysType.calendar_days:
        return (date2 - date).days

    # Generate all days between date and date2
    daygenerator = (date + datetime.timedelta(x) for x in range((date2 - date).days))

    # Calculate the number of weekdays (Monday to Friday) between date and date2
    return sum(1 for day in daygenerator if day.weekday() < 5)
