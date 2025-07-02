from typing import Annotated

from fastapi import APIRouter, Depends, Path
from meldingen_core.wfs import WfsProviderFactory
from starlette.exceptions import HTTPException
from starlette.responses import StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen_core.models import AssetType
from meldingen.wfs import WfsProvider

router = APIRouter()


@router.get(
    "/{slug}",
    name="asset:retrieve",
    responses={**unauthorized_response, **not_found_response},
    response_class=StreamingResponse,
    dependencies=[Depends(authenticate_user)],
)
async def retrieve_asset(
    slug: Annotated[str, Path(description="The slug of the attachment.", min_length=1)],
    type_names: str = "app:container",
    count: int = 1000,
    srs_name: str = "urn:ogc:def:crs:EPSG::4326",
    output_format: str = "application/json",
    filter: str | None = None,
) -> StreamingResponse:
    if slug != "container":
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    url = "https://api.data.amsterdam.nl/v1/wfs/huishoudelijkafval"
    asset_type = AssetType(slug, "meldingen.api.v1.endpoints.asset.ContainerWfsClient", {"base_url": url})

    factory = WfsProviderFactory()
    wfs_provider = factory(asset_type)

    iterator, media_type = await wfs_provider(type_names, count, srs_name, output_format, filter)

    return StreamingResponse(iterator, media_type=media_type)


class ContainerWfsClient(WfsProvider):
    ...
