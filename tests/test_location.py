from unittest.mock import AsyncMock, Mock

import pytest
from geoalchemy2 import WKBElement
from geojson_pydantic import Point as GeoJsonPoint
from geojson_pydantic.types import Position2D
from shapely.geometry import Point as ShapelyPoint

from meldingen.location import (
    GeoJsonFeatureFactory,
    GeoJSONToShapeTransformer,
    GeoJSONToWKBTransformer,
    MeldingLocationIngestor,
    ShapePointFactory,
    ShapeToGeoJSONTransformer,
    ShapeToWKBTransformer,
)
from meldingen.models import Melding
from meldingen.repositories import MeldingRepository
from meldingen.schemas import GeoJson


@pytest.mark.anyio
async def test_geojson_feature_factory():
    factory = GeoJsonFeatureFactory()
    point = GeoJsonPoint(type="Point", coordinates=[52.3680605, 4.897092])
    feature = factory(point)

    assert feature.type == "Feature"
    assert feature.geometry == point
    assert feature.properties == {}


@pytest.mark.anyio
async def test_shape_point_factory():
    factory = ShapePointFactory()
    point = factory(52.3680605, 4.897092)

    assert isinstance(point, ShapelyPoint)
    assert point.x == 52.3680605
    assert point.y == 4.897092


@pytest.mark.anyio
async def test_geojson_to_shape_transformer():
    point_factory = ShapePointFactory()
    transform = GeoJSONToShapeTransformer(point_factory)
    geojson = GeoJson(
        type="Feature", geometry=GeoJsonPoint(type="Point", coordinates=[52.3680605, 4.897092]), properties={}
    )

    shape = transform(geojson)

    assert isinstance(shape, ShapelyPoint)
    assert shape.x == 52.3680605
    assert shape.y == 4.897092


@pytest.mark.anyio
async def test_shape_to_wkb_transformer():
    transform = ShapeToWKBTransformer()
    shape = ShapelyPoint(52.3680605, 4.897092)
    wkb_element = transform(shape)

    assert isinstance(wkb_element, WKBElement)


@pytest.mark.anyio
async def test_geojson_to_wkb_transformer():
    geojson_to_shape = GeoJSONToShapeTransformer(ShapePointFactory())
    shape_to_wkb = ShapeToWKBTransformer()
    transform = GeoJSONToWKBTransformer(geojson_to_shape, shape_to_wkb)
    geojson = GeoJson(
        type="Feature", geometry=GeoJsonPoint(type="Point", coordinates=[52.3680605, 4.897092]), properties={}
    )

    wkb_element = transform(geojson)

    assert isinstance(wkb_element, WKBElement)
    assert wkb_element.srid == 4326
    assert bytes(wkb_element.data) == (b"\x01\x01\x00\x00\x00\x869A\x9b\x1c/J@O\x03\x06I\x9f\x96\x13@")


@pytest.mark.anyio
def test_shape_to_geojson_transformer():
    geojson_factory = GeoJsonFeatureFactory()
    transform = ShapeToGeoJSONTransformer(geojson_factory)
    shape = ShapelyPoint(52.3680605, 4.897092)
    geojson = transform(shape)

    assert isinstance(geojson, GeoJson)
    assert geojson.geometry.type == "Point"
    assert geojson.geometry.coordinates == Position2D(longitude=52.3680605, latitude=4.897092)


@pytest.mark.anyio
async def test_melding_location_ingestor():
    melding = Mock(Melding)
    melding_repository = AsyncMock(MeldingRepository)
    point_factory = ShapePointFactory()
    geojson_to_shape = GeoJSONToShapeTransformer(point_factory)
    shape_to_wkb = ShapeToWKBTransformer()
    ingestor = MeldingLocationIngestor(melding_repository, geojson_to_shape, shape_to_wkb)

    geojson = GeoJson(type="Feature", geometry={"type": "Point", "coordinates": [52.3680605, 4.897092]}, properties={})

    await ingestor(melding, geojson)

    assert melding.geo_location is not None
    melding_repository.save.assert_awaited_once_with(melding)
