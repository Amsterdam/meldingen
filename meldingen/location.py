import json
from typing import Tuple

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from shapely import Geometry, Point, Polygon, to_geojson

from meldingen.models import Melding
from meldingen.repositories import MeldingRepository
from meldingen.schemas import MeldingLocationInput


class MeldingLocationIngestor:
    """
    This class describes the ingestion flow of a location of a Melding.
    It will take in a geojson object and convert it to a shape.
    The shape object can be used for further validation and processing.
    Eventually the shape will be converted to a WKB element which is stored in the database.
    """

    _repository: MeldingRepository
    _geojson_to_shape: "GeoJSONToShapeTransformer"
    _shape_to_wkb: "ShapeToWKBTransformer"

    def __init__(
        self,
        melding_repository: MeldingRepository,
        geojson_to_shape_transformer: "GeoJSONToShapeTransformer",
        shape_to_wkb_transformer: "ShapeToWKBTransformer",
    ):
        self._repository = melding_repository
        self._geojson_to_shape_transformer = geojson_to_shape_transformer
        self._shape_to_wkb_transformer = shape_to_wkb_transformer

    async def __call__(self, melding: Melding, geojson: MeldingLocationInput) -> Melding:
        shape = self._geojson_to_shape_transformer(geojson)
        wkb_element = self._shape_to_wkb_transformer(shape)

        melding.geo_location = wkb_element
        await self._repository.save(melding)

        return melding


class LocationOutputTransformer:
    """
    This class describes the response flow of a location of a Melding.
    It will take in a WKB element and convert it to a shape.
    Eventually the shape will be converted to a geojson object which is returned to the client.
    """

    _wkb_to_shape: "WKBToShapeTransformer"
    _shape_to_geojson: "ShapeToGeoJSONTransformer"

    def __init__(
        self,
        wkb_to_shape_transformer: "WKBToShapeTransformer",
        shape_to_geojson_transformer: "ShapeToGeoJSONTransformer",
    ):
        self._wkb_to_shape_transformer = wkb_to_shape_transformer
        self._shape_to_geojson_transformer = shape_to_geojson_transformer

    def __call__(self, geo_location: WKBElement | None) -> dict | None:
        if geo_location is None:
            return geo_location

        shape = self._wkb_to_shape_transformer(geo_location)
        geojson = self._shape_to_geojson_transformer(shape)

        return geojson


class GeoJSONToShapeTransformer:
    _generate_point: "ShapePointFactory"
    _generate_polygon: "ShapePolygonFactory"

    def __init__(self, point_factory: "ShapePointFactory", polygon_factory: "ShapePolygonFactory"):
        self._generate_point = point_factory
        self._generate_polygon = polygon_factory

    def __call__(self, geojson: MeldingLocationInput) -> Geometry:
        print(geojson)
        match geojson.root.geometry.type:
            case "Point":
                return self._generate_point(*geojson.root.geometry.coordinates)
            case "Polygon":
                return self._generate_polygon(*geojson.root.geometry.coordinates[0])
            case _:
                raise ValueError("Invalid GeoJSON type")


class ShapeToWKBTransformer:
    _spatial_ref_id: int

    def __init__(self, spatial_ref_id: int = 4326) -> None:
        self._spatial_ref_id = spatial_ref_id

    def __call__(self, shape: Geometry) -> WKBElement:
        return from_shape(shape, self._spatial_ref_id)


class GeoJSONToWKBTransformer:
    _geojson_to_shape: GeoJSONToShapeTransformer
    _shape_to_wkb: ShapeToWKBTransformer

    def __init__(self, geojson_to_shape: GeoJSONToShapeTransformer, shape_to_wkb: ShapeToWKBTransformer):
        self._geojson_to_shape = geojson_to_shape
        self._shape_to_wkb = shape_to_wkb

    def __call__(self, geojson: MeldingLocationInput) -> WKBElement:
        shape = self._geojson_to_shape(geojson)
        return self._shape_to_wkb(shape)


class ShapeToGeoJSONTransformer:

    def __call__(self, shape: Geometry) -> dict:
        return json.loads(to_geojson(shape))


class WKBToShapeTransformer:

    def __call__(self, wkb_element: WKBElement) -> Geometry:
        return to_shape(wkb_element)


class ShapePointFactory:

    def __call__(self, lat: float, long: float) -> Point:
        return Point(lat, long)


class ShapePolygonFactory:

    def __call__(self, points: list[Tuple[float, float]]) -> Polygon:
        return Polygon(points)
