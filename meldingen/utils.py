import datetime
from typing import Any


class SafeTemplateDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def format_safe(template: str, mapping: dict[str, Any]) -> str:
    return template.format_map(SafeTemplateDict(mapping))


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


def utc_datetime(*args: int) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=datetime.UTC)
