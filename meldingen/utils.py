import datetime
from collections.abc import Callable
from typing import Any

from babel.dates import format_datetime
from meldingen_core.address import Address

from meldingen.address import AddressFormatter
from meldingen.config import settings
from meldingen.models import Melding


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def utc_datetime(*args) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=datetime.UTC)


def format_date_time(date_time: datetime.datetime, format: str) -> str:
    return format_datetime(date_time, format=format, locale=settings.date_time_format_locale)


def format_readable_date_time(date_time: datetime.datetime) -> str:
    return format_date_time(date_time, format=settings.date_time_format_readable_format)


def pick_class_attributes(cls, *keys: str, __predicate: Callable[[str, Any], bool] | None = None) -> dict[str, Any]:
    attr = {}
    for attribute in keys:
        value = getattr(cls, attribute)
        if __predicate and not __predicate(attribute, value):
            continue
        attr[attribute] = value

    return attr


def extract_melding_address(melding: Melding) -> Address | None:
    keys_required = ("city", "street", "house_number", "postal_code")
    keys = (*keys_required, "house_number_addition")
    address_attr = pick_class_attributes(
        melding, *keys, __predicate=lambda k, v: v is not None and isinstance(v, str | int)
    )

    if not address_attr or len(address_attr) < len(keys_required):
        return None

    return Address(**address_attr)


def format_melding_address(melding: Melding, format: str = settings.default_address_format) -> str | None:
    address = extract_melding_address(melding)
    return AddressFormatter(address).format(format) if address else None
