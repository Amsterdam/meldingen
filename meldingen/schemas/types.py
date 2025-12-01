from typing import Annotated, Any, TypeAlias

from geojson_pydantic import Feature as GeoJsonPydanticFeature
from geojson_pydantic import Point
from meldingen_core.address import Address as BaseAddress
from pydantic import BaseModel, Field, StringConstraints, AfterValidator
from pydantic.dataclasses import dataclass
from pydantic_extra_types.phone_numbers import PhoneNumber as PydanticPhoneNumber

from meldingen.config import settings


class GeoJson(GeoJsonPydanticFeature[Point, dict[str, Any] | BaseModel]): ...


@dataclass
class Address(BaseAddress):
    house_number: int = Field(gt=0)


StrippedStr: TypeAlias = Annotated[str, AfterValidator(lambda val: val.strip())]
"""String that automatically strips leading and trailing whitespace. May be empty."""

NonEmptyStrippedStr: TypeAlias = Annotated[StrippedStr, StringConstraints(min_length=1)]
"""String that's automatically strips leading and trailing whitespace. Must not be empty."""


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
    show: bool
    when: NonEmptyStrippedStr
    eq: str | int | float | bool | None
