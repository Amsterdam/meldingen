from typing import Any

from geojson_pydantic import Feature as GeoJsonPydanticFeature
from geojson_pydantic import Point
from pydantic import BaseModel
from pydantic_extra_types.phone_numbers import PhoneNumber as PydanticPhoneNumber

from meldingen.config import settings


class GeoJson(GeoJsonPydanticFeature[Point, dict[str, Any] | BaseModel]): ...


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
