from typing import AsyncIterator, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import APIRouter, Depends
from httpx import AsyncClient
from meldingen_core.wfs import BaseWfsProvider
from starlette.responses import StreamingResponse

from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user

router = APIRouter()

# TODO:: Make this generic for all Wfs API providers.
#  Pretty much all of this can be in a base class, none is specific to Container.
class ContainerWfsAsset(BaseWfsProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url
        pass

    # TODO:: Should this action come from core? At least from some abstraction?
    async def action(
        self,
        type_names: str = "app:container",
        count: int = 1000,
        srs_name: str = "urn:ogc:def:crs:EPSG::4326",
        output_format: str = "application/json",
        filter: str | None = None,
    ) -> StreamingResponse:
        iterator, media_type = await self(
            type_names=type_names,
            count=count,
            srs_name=srs_name,
            output_format=output_format,
            filter=filter,
        )

        return StreamingResponse(iterator, media_type=media_type)


    async def __call__(
        self,
        type_names: str = "app:container",
        count: int = 1000,
        srs_name: str = "urn:ogc:def:crs:EPSG::4326",
        output_format: str = "application/json",
        filter: str | None = None,
    ) -> Tuple[AsyncIterator[bytes], str]:
        url = self.get_url(self.base_url, type_names, count, srs_name, output_format, filter)

        iterator = self.stream_data_from_url(url)

        return iterator, output_format


    async def stream_data_from_url(self, url: str) -> AsyncIterator[bytes]:
        async with AsyncClient() as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                async for chunk in response.aiter_bytes():
                    yield chunk


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
        # TODO:: Should these be hardcoded, or also be added as params from core?
        query.append(("SERVICE", "WFS"))
        query.append(("REQUEST", "GetFeature"))
        query.append(("VERSION", "2.0.0"))
        query.append(("TYPENAMES", type_names))
        query.append(("SRSNAME", srs_name))
        query.append(("OUTPUTFORMAT", output_format))

        query.append(("COUNT", str(count)))
        query.append(("FILTERS", filter))

        new_query = urlencode(query)

        new_url = urlunparse(parsed_url._replace(query=new_query))

        return str(new_url)


# TODO:: Get this from asset type params with the WfsProviderFactory
container_asset = ContainerWfsAsset("https://api.data.amsterdam.nl/v1/wfs/huishoudelijkafval")

# TODO:: Check if this is the right way to do a route from a class
#   Maybe the route action can be outside of the class entirely, and just call the class?
router.add_api_route(
    "/container",
    container_asset.action,
    name="asset:container:retrieve",
    responses={**unauthorized_response, **not_found_response},
    response_class=StreamingResponse,
    dependencies=[Depends(authenticate_user)],
)
