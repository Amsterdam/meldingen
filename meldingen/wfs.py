from typing import AsyncIterator, Literal, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from meldingen_core.wfs import BaseWfsProvider

from meldingen.api.utils import stream_data_from_url


# The base class provides everything we need to get the Wfs from a proxy, so all we need to do is to extend it.
# Database class_name in AssetType: 'meldingen.wfs.ProxyWfsProvider'
# Database arguments example in AssetType: '{"base_url": "https://api.data.amsterdam.nl/v1/wfs/huishoudelijkafval"}'
class ProxyWfsProvider(BaseWfsProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def __call__(
        self,
        type_names: str,
        count: int = 1000,
        srs_name: str = "urn:ogc:def:crs:EPSG::4326",
        output_format: str = "application/json",
        service: Literal["WFS"] = "WFS",
        version: str = "2.0.0",
        request: Literal["GetFeature"] = "GetFeature",
        filter: str | None = None,
    ) -> AsyncIterator[bytes]:
        url = self.get_url(self.base_url, type_names, count, srs_name, output_format, service, version, request, filter)

        return stream_data_from_url(url)

    def get_url(
        self,
        base_url: str,
        type_names: str,
        count: int = 1000,
        srs_name: str = "urn:ogc:def:crs:EPSG::4326",
        output_format: str = "application/json",
        service: Literal["WFS"] = "WFS",
        version: str = "2.0.0",
        request: Literal["GetFeature"] = "GetFeature",
        filter: str | None = None,
    ) -> str:
        parsed_url = urlparse(base_url)

        query = parse_qsl(parsed_url.query)

        query.append(("TYPENAMES", type_names))
        query.append(("SRSNAME", srs_name))
        query.append(("OUTPUTFORMAT", output_format))
        query.append(("SERVICE", service))
        query.append(("REQUEST", request))
        query.append(("VERSION", version))
        query.append(("COUNT", str(count)))

        if filter is not None:
            query.append(("FILTERS", filter))

        new_query = urlencode(query)

        new_url = urlunparse(parsed_url._replace(query=new_query))

        return str(new_url)
