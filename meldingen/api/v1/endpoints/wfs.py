from typing import Annotated, AsyncIterator, Literal

from fastapi import APIRouter, Depends, Path
from meldingen_core.actions.wfs import WfsRetrieveAction
from meldingen_core.exceptions import NotFoundException
from starlette.exceptions import HTTPException
from starlette.responses import StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import wfs_retrieve_action
from meldingen.schemas.types import GeoJson

router = APIRouter()


@router.get(
    "/{name}",
    name="wfs:retrieve",
    responses={**unauthorized_response, **not_found_response},
    response_class=StreamingResponse,
    response_model=GeoJson,
    dependencies=[Depends(authenticate_user)],
)
async def retrieve_wfs(
    action: Annotated[WfsRetrieveAction, Depends(wfs_retrieve_action)],
    name: Annotated[str, Path(description="The name of the asset type.", min_length=1)],
    type_names: str = "app:container",
    count: int = 1000,
    srs_name: str = "urn:ogc:def:crs:EPSG::4326",
    output_format: str = "application/json",
    service: Literal["WFS"] = "WFS",
    version: str = "2.0.0",
    request: Literal["GetFeature"] = "GetFeature",
    filter: str | None = None,
) -> StreamingResponse:
    try:
        iterator = await action(name, type_names, count, srs_name, output_format, service, version, request, filter)
    except NotFoundException as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e)) from e

    return StreamingResponse(iterator, media_type=output_format)
