from typing import AsyncIterator, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from meldingen_core.wfs import BaseWfsProvider

from meldingen.api.utils import stream_data_from_url

# TODO:: Should these be hardcoded, or also be added as params from core?
SERVICE = "WFS"
VERSION = "2.0.0"
REQUEST = "GetFeature"


class WfsProvider(BaseWfsProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def __call__(
        self,
        type_names: str = "app:container",
        count: int = 1000,
        srs_name: str = "urn:ogc:def:crs:EPSG::4326",
        output_format: str = "application/json",
        filter: str | None = None,
    ) -> Tuple[AsyncIterator[bytes], str]:
        url = self.get_url(self.base_url, type_names, count, srs_name, output_format, filter)

        iterator = stream_data_from_url(url)

        return iterator, output_format

    # TODO:: Check if this is okay to parse the url
    def get_url(
        self,
        base_url: str,
        type_names: str = "app:container",
        count: int = 1000,
        srs_name: str = "urn:ogc:def:crs:EPSG::4326",
        output_format: str = "application/json",
        filter: str | None = None,
    ):
        parsed_url = urlparse(base_url)

        query = parse_qsl(parsed_url.query)

        query.append(("SERVICE", SERVICE))
        query.append(("REQUEST", REQUEST))
        query.append(("VERSION", VERSION))
        query.append(("TYPENAMES", type_names))
        query.append(("SRSNAME", srs_name))
        query.append(("OUTPUTFORMAT", output_format))
        query.append(("COUNT", str(count)))
        query.append(("FILTERS", filter))

        new_query = urlencode(query)

        new_url = urlunparse(parsed_url._replace(query=new_query))

        return str(new_url)
