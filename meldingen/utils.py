import datetime
from typing import Any

from meldingen.models import ServiceLevelObjectiveDayType


class SafeTemplateDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def format_safe(template: str, mapping: dict[str, Any]) -> str:
    return template.format_map(SafeTemplateDict(mapping))


def days_passed_since(
    date: datetime.date,
    date2: datetime.date | None,
    days_type: ServiceLevelObjectiveDayType = ServiceLevelObjectiveDayType.calendar_days,
) -> int:
    """Count days in the half-open interval [date, date2) according to the specified day type.

    The start date is included. The end date is excluded.
    If date2 is None, the current UTC date is used.

    Holidays are never taken into account.
    """

    if date2 is None:
        date2 = datetime.datetime.now(datetime.UTC).date()

    # Calendar days, all days are counted
    if days_type == ServiceLevelObjectiveDayType.calendar_days:
        return (date2 - date).days

    # Workdays, excluding weekends
    daygenerator = (
        date + datetime.timedelta(x) for x in range((date2 - date).days)
    )  # generate days in [d1, d2), matching numpy.busday_count

    return sum(1 for day in daygenerator if day.weekday() < 5)
