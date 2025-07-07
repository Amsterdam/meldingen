from typing import AsyncIterator, Literal, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from meldingen_core.wfs import BaseWfsProvider

from meldingen.api.utils import stream_data_from_url


class UrlProcessor:
    def __call__(
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


class ProxyWfsProvider(BaseWfsProvider):
    _base_url: str
    _get_url: UrlProcessor

    def __init__(self, base_url: str, url_processor: UrlProcessor):
        self._base_url = base_url
        self._get_url = url_processor

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
        url = self._get_url(self._base_url, type_names, count, srs_name, output_format, service, version, request, filter)

        return stream_data_from_url(url)
