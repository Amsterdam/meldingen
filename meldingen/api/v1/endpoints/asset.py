from typing import Tuple, AsyncIterator

from fastapi import APIRouter, Depends, Request
from httpx import AsyncClient
from meldingen_core.wfs import BaseWfsProvider
from starlette.responses import RedirectResponse, Response, StreamingResponse

from meldingen.api.v1 import unauthorized_response, not_found_response
from meldingen.authentication import authenticate_user
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

router = APIRouter()


class ContainerWfsAsset(BaseWfsProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url
        pass

    async def action(self):
        iterator, media_type = await self()

        return StreamingResponse(iterator, media_type=media_type)

    async def __call__(
        self,
        type_names: str = "app:container",
        count: int = 1000,
        srs_name: str = "urn:ogc:def:crs:EPSG::4326",
        output_format: str = "application/json",
        filter: str | None = None,
    ) -> Tuple[AsyncIterator[bytes], str]:
        url = self.get_url(
            self.base_url,
            type_names,
            count,
            srs_name,
            output_format,
            filter
        )

        iterator = self.stream_data_from_url(url)

        return iterator, output_format


    async def stream_data_from_url(self, url: str) -> AsyncIterator[bytes]:
        """
        Stream data from a URL using an asynchronous iterator.
        """
        async with AsyncClient() as client:
            async with client.stream("GET", url) as response:
                # Raise an exception if the response status is not 200
                response.raise_for_status()

                # Iterate over the response content in chunks
                async for chunk in response.aiter_bytes():
                    yield chunk


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
        query.append(("SERVICE", "WFS"))
        query.append(("REQUEST", "GetFeature"))
        query.append(("VERSION", "2.0.0"))
        query.append(("TYPENAMES", type_names))
        query.append(("SRSNAME", srs_name))
        query.append(("OUTPUTFORMAT", output_format))

        query.append(("COUNT", str(2)))
        query.append(("FILTERS", filter))

        new_query = urlencode(query)

        new_url = urlunparse(parsed_url._replace(query=new_query))

        return str(new_url)


# TODO:: Get this from asset type params with the WfsProviderFactory
container_asset = ContainerWfsAsset("https://api.data.amsterdam.nl/v1/wfs/huishoudelijkafval")

router.add_api_route(
    "/container",
    container_asset.action,
    name="asset:container:retrieve",
    responses={**unauthorized_response, **not_found_response},
    response_class=StreamingResponse,
    dependencies=[Depends(authenticate_user)],
)