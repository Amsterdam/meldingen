import json

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from geojson_pydantic import Point as GeoJsonPoint
from shapely import Geometry, Point, to_geojson

from meldingen.models import Melding
from meldingen.repositories import MeldingRepository
from meldingen.schemas.types import GeoJson


class GeoJsonFeatureFactory:

    def __call__(self, geometry: GeoJsonPoint) -> GeoJson:
        return GeoJson(
            type="Feature",
            geometry=geometry,
            properties={},
        )


class ShapePointFactory:

    def __call__(self, lat: float, long: float) -> Point:
        return Point(lat, long)


class ShapeToWKBTransformer:
    _spatial_ref_id: int

    def __init__(self, spatial_ref_id: int = 4326) -> None:
        self._spatial_ref_id = spatial_ref_id

    def __call__(self, shape: Geometry) -> WKBElement:
        return from_shape(shape, self._spatial_ref_id)


class ShapeToGeoJSONTransformer:
    _transform_to_geojson: GeoJsonFeatureFactory

    def __init__(self, geojson_factory: GeoJsonFeatureFactory) -> None:
        self._transform_to_geojson = geojson_factory

    def __call__(self, shape: Geometry) -> GeoJson:
        geometry = json.loads(to_geojson(shape))

        return self._transform_to_geojson(geometry=geometry)


class WKBToShapeTransformer:

    def __call__(self, wkb_element: WKBElement) -> Geometry:
        shape = to_shape(wkb_element)
        assert isinstance(shape, Geometry)
        return shape


class MeldingLocationIngestor:
    """
    This class describes the ingestion flow of a location of a Melding.
    It will take in a geojson object and convert it to a shape.
    The shape object can be used for further validation and processing.
    Eventually the shape will be converted to a WKB element which is stored in the database.
    """

    _repository: MeldingRepository
    _geojson_to_shapely_point: ShapePointFactory
    _shape_to_wkb: ShapeToWKBTransformer

    def __init__(
        self,
        melding_repository: MeldingRepository,
        shape_point_factory: ShapePointFactory,
        shape_to_wkb_transformer: ShapeToWKBTransformer,
    ) -> None:
        self._repository = melding_repository
        self._geojson_to_shapely_point = shape_point_factory
        self._shape_to_wkb_transformer = shape_to_wkb_transformer

    async def __call__(self, melding: Melding, geojson: GeoJson) -> Melding:
        if geojson.geometry is None:
            return melding

        shape = self._geojson_to_shapely_point(*geojson.geometry.coordinates)
        wkb_element = self._shape_to_wkb_transformer(shape)
        assert isinstance(wkb_element, WKBElement)

        melding.geo_location = wkb_element
        await self._repository.save(melding)

        return melding


class LocationOutputTransformer:
    """
    This class describes the response flow of a location of a Melding.
    It will take in a WKB element and convert it to a shape.
    Eventually the shape will be converted to a geojson object which is returned to the client.
    """

    _wkb_to_shape: WKBToShapeTransformer
    _shape_to_geojson: ShapeToGeoJSONTransformer

    def __init__(
        self,
        wkb_to_shape_transformer: WKBToShapeTransformer,
        shape_to_geojson_transformer: ShapeToGeoJSONTransformer,
    ) -> None:
        self._wkb_to_shape_transformer = wkb_to_shape_transformer
        self._shape_to_geojson_transformer = shape_to_geojson_transformer

    def __call__(self, geo_location: WKBElement | None) -> GeoJson | None:
        if geo_location is None:
            return geo_location

        shape = self._wkb_to_shape_transformer(geo_location)
        geojson = self._shape_to_geojson_transformer(shape)

        return geojson
