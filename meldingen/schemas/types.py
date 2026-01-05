import datetime
import re
from typing import Annotated, Any, TypeAlias

from geojson_pydantic import Feature as GeoJsonPydanticFeature
from geojson_pydantic import Point
from meldingen_core.address import Address as BaseAddress
from pydantic import AfterValidator, BaseModel, Field, StringConstraints, field_validator
from pydantic.dataclasses import dataclass
from pydantic_extra_types.phone_numbers import PhoneNumber as PydanticPhoneNumber

from meldingen.config import settings


class GeoJson(GeoJsonPydanticFeature[Point, dict[str, Any] | BaseModel]): ...


@dataclass
class Address(BaseAddress):
    house_number: int = Field(gt=0)


class PhoneNumber(PydanticPhoneNumber):
    default_region_code = settings.phone_number_default_region_code
    phone_format = settings.phone_number_format

    # If format is E164 and region code is NL
    # It will accept:
    # 06 12345678
    # 020 1234567
    # +31 6 12345678
    # +31 20 1234567

    # Will return:
    # +31612345678
    # +31201234567


class FormIOConditional(BaseModel):
    show: bool | None
    when: Annotated[str, StringConstraints(strip_whitespace=True)] | None
    eq: str | int | float | bool | None


class InvalidDateFormatException(Exception):
    """Raised when a date is not in the expected format."""

    def __init__(self, msg: str, input: dict[str, Any]) -> None:
        self.msg = msg
        self.input = input


class DateAnswerObject(BaseModel):
    """Used to display an answer in a date answer component."""

    value: str  # the raw value selected by the user f.e. "day -1"
    label: str
    converted_date: str  # ISO 8601 formatted date

    @field_validator("converted_date")
    @classmethod
    def validate_converted_date(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise InvalidDateFormatException(
                msg="converted_date must be in YYYY-mm-dd format", input={"converted_date": value}
            )
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise InvalidDateFormatException(
                msg="converted_date must be in YYYY-mm-dd format", input={"converted_date": value}
            )
        return value


class ValueLabelObject(BaseModel):
    """Used to display an answer in a value label answer component."""

    value: str
    label: str
