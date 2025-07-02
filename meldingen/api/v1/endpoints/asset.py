from typing import Annotated

from fastapi import APIRouter, Depends, Path
from meldingen_core.actions.asset import AssetRetrieveAction
from starlette.exceptions import HTTPException
from starlette.responses import StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user

from meldingen.dependencies import asset_retrieve_action
from meldingen.wfs import WfsProvider

router = APIRouter()


@router.get(
    "/{name}",
    name="asset:retrieve",
    responses={**unauthorized_response, **not_found_response},
    response_class=StreamingResponse,
    dependencies=[Depends(authenticate_user)],
)
async def retrieve_asset(
    action: Annotated[AssetRetrieveAction, Depends(asset_retrieve_action)],
    name: Annotated[str, Path(description="The name of the asset.", min_length=1)],
    type_names: str = "app:container",
    count: int = 1000,
    srs_name: str = "urn:ogc:def:crs:EPSG::4326",
    output_format: str = "application/json",
    filter: str | None = None,
) -> StreamingResponse:
    if name != "container":
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await action(name, type_names, count, srs_name, output_format, filter)


class ContainerWfsClient(WfsProvider):
    ...
