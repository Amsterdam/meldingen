from unittest.mock import AsyncMock, Mock

import pytest
from geoalchemy2 import WKBElement
from geojson_pydantic import Point as GeoJsonPoint
from geojson_pydantic.types import Position2D
from shapely.geometry import Point as ShapelyPoint

from meldingen.location import (
    GeoJsonFeatureFactory,
    MeldingLocationIngestor,
    ShapePointFactory,
    ShapeToGeoJSONTransformer,
    ShapeToWKBTransformer,
)
from meldingen.models import Melding
from meldingen.repositories import MeldingRepository
from meldingen.schemas.types import GeoJson


def test_geojson_feature_factory() -> None:
    factory = GeoJsonFeatureFactory()
    point = GeoJsonPoint(type="Point", coordinates=[52.3680605, 4.897092])
    feature = factory(point)

    assert feature.type == "Feature"
    assert feature.geometry == point
    assert feature.properties == {}


def test_shape_point_factory() -> None:
    factory = ShapePointFactory()
    point = factory(52.3680605, 4.897092)

    assert isinstance(point, ShapelyPoint)
    assert point.x == 52.3680605
    assert point.y == 4.897092


def test_shape_to_wkb_transformer() -> None:
    transform = ShapeToWKBTransformer()
    shape = ShapelyPoint(52.3680605, 4.897092)
    wkb_element = transform(shape)

    assert isinstance(wkb_element, WKBElement)


def test_shape_to_geojson_transformer() -> None:
    geojson_factory = GeoJsonFeatureFactory()
    transform = ShapeToGeoJSONTransformer(geojson_factory)
    shape = ShapelyPoint(52.3680605, 4.897092)
    geojson = transform(shape)

    assert isinstance(geojson, GeoJson)
    assert geojson.geometry is not None
    assert geojson.geometry.type == "Point"
    assert geojson.geometry.coordinates == Position2D(longitude=52.3680605, latitude=4.897092)


@pytest.mark.anyio
async def test_melding_location_ingestor() -> None:
    melding = Mock(Melding)
    melding_repository = AsyncMock(MeldingRepository)
    point_factory = ShapePointFactory()
    shape_to_wkb = ShapeToWKBTransformer()
    geojson = GeoJson(type="Feature", geometry={"type": "Point", "coordinates": [52.3680605, 4.897092]}, properties={})

    ingest = MeldingLocationIngestor(melding_repository, point_factory, shape_to_wkb)
    await ingest(melding, geojson)

    assert melding.geo_location is not None
    melding_repository.save.assert_awaited_once_with(melding)
