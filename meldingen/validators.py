from functools import cache
from pathlib import Path
from typing import Annotated, Any, Callable

from geojson_pydantic import Point as GeoJsonPydanticPoint
from shapely import MultiPolygon
from shapely import Point as ShapelyPoint
from shapely import Polygon, from_geojson, from_wkt


def create_match_validator(match_value: Any, error_msg: str) -> Callable[[Any], Any]:
    """
    Create a validator function that checks if a value matches a given match_value.

    Examples:
    >>> validate = create_match_validator(5, "Value must be {match_value}")
    >>> validate(5)
    5
    >>> validate(6)
    AssertionError: Value must be 5
    """

    def validator(value: Any) -> Any:
        assert value == match_value, error_msg.format(value=value, match_value=match_value)
        return value

    return validator


def create_non_match_validator(match_value: Any, error_msg: str) -> Callable[[Any], Any]:
    """
    Create a validator function that checks if a value does not match a given match_value.

    Examples:
    >>> validate = create_non_match_validator("Hello", "Value must not match {match_value}")
    >>> validate("Hello")
    AssertionError: Value must not be 'Hello'
    >>> validate("world")
    'world'
    """

    def validator(value: Any) -> Any:
        assert value != match_value, error_msg.format(value=value, match_value=match_value)
        return value

    return validator


@cache
def load_geojson(path: str | Path) -> Polygon | MultiPolygon:
    """Load polygon from geojson file."""
    with open(path, "r") as f:
        shape = from_geojson(f.read())
    return shape


def within_polygon(
    geometry: Annotated[str | ShapelyPoint | GeoJsonPydanticPoint, "Geometry in WKT format"],
    shape: Polygon | MultiPolygon,
) -> None:
    """Check if the given geometry is within the (multi) polygon defined in the geojson file"""
    if not isinstance(geometry, (str, ShapelyPoint, GeoJsonPydanticPoint)):
        raise TypeError(
            'geometry must be as a `str` in the "Well Known Text" format OR as a (shapely/geojson_pydantic) Point object'
        )

    if isinstance(geometry, str):
        geometry = from_wkt(geometry)

    if isinstance(geometry, GeoJsonPydanticPoint):
        geometry = from_wkt(geometry.wkt)

    assert geometry.within(shape), "given geometry must be within the configured (multi) polygon"
