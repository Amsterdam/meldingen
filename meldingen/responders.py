from meldingen.location import LocationOutputTransformer
from meldingen.models import Melding
from meldingen.schemas import MeldingOutput


class MeldingResponder:

    def __init__(self, location_transformer: LocationOutputTransformer):
        self.transform_location = location_transformer

    def __call__(self, melding: Melding) -> MeldingOutput:
        if melding.geo_location is None:
            geojson_location = None
        else:
            geojson_location = self.transform_location(melding.geo_location)

        return MeldingOutput(
            id=melding.id,
            text=melding.text,
            state=melding.state,
            classification=melding.classification_id,
            created_at=melding.created_at,
            updated_at=melding.updated_at,
            geo_location=geojson_location,
        )
