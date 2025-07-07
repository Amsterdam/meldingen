from typing import AsyncIterator, Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from httpx import AsyncClient, Response
from meldingen_core.wfs import BaseWfsProvider, BaseWfsProviderFactory


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
    _client: AsyncClient

    def __init__(self, base_url: str, url_processor: UrlProcessor, client: AsyncClient):
        self._base_url = base_url
        self._get_url = url_processor
        self._client = client

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
        url = self._get_url(
            self._base_url, type_names, count, srs_name, output_format, service, version, request, filter
        )

        http_request = self._client.build_request("GET", url)
        response = await self._client.send(http_request, stream=True)
        response.raise_for_status()

        async def iterator(response: Response) -> AsyncIterator[bytes]:
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()

        return iterator(response)


class ProxyWfsProviderFactory(BaseWfsProviderFactory):
    _base_url: str

    def __init__(self, base_url: str):
        self._base_url = base_url

    def __call__(self) -> ProxyWfsProvider:
        return ProxyWfsProvider(self._base_url, UrlProcessor(), AsyncClient())
