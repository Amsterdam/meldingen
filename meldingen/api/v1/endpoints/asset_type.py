from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from geojson_pydantic import FeatureCollection
from meldingen_core.exceptions import NotFoundException
from starlette.responses import StreamingResponse
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from meldingen.actions.asset_type import (
    AssetTypeCreateAction,
    AssetTypeDeleteAction,
    AssetTypeListAction,
    AssetTypeRetrieveAction,
    AssetTypeUpdateAction,
    WfsRetrieveAction,
)
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import conflict_response, list_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import (
    asset_type_create_action,
    asset_type_delete_action,
    asset_type_list_action,
    asset_type_output_factory,
    asset_type_repository,
    asset_type_retrieve_action,
    asset_type_update_action,
    wfs_retrieve_action,
)
from meldingen.models import AssetType
from meldingen.repositories import AssetTypeRepository
from meldingen.schemas.input import AssetTypeInput, AssetTypeUpdateInput
from meldingen.schemas.output import AssetTypeOutput
from meldingen.schemas.output_factories import AssetTypeOutputFactory

router = APIRouter()


@router.post(
    "/",
    name="asset-type:create",
    status_code=HTTP_201_CREATED,
    responses={**unauthorized_response, **conflict_response},
    dependencies=[Depends(authenticate_user)],
)
async def create_asset_type(
    input: AssetTypeInput,
    action: Annotated[AssetTypeCreateAction, Depends(asset_type_create_action)],
    produce_output: Annotated[AssetTypeOutputFactory, Depends(asset_type_output_factory)],
) -> AssetTypeOutput:
    asset_type = AssetType(**input.model_dump())

    await action(asset_type)

    return produce_output(asset_type)


@router.get(
    "/{asset_type_id}",
    name="asset-type:retrieve",
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
async def retrieve_asset_type(
    asset_type_id: Annotated[int, Path(description="The asset type id.", ge=1)],
    action: Annotated[AssetTypeRetrieveAction, Depends(asset_type_retrieve_action)],
    produce_output: Annotated[AssetTypeOutputFactory, Depends(asset_type_output_factory)],
) -> AssetTypeOutput:
    asset_type = await action(asset_type_id)
    if asset_type is None:
        raise HTTPException(HTTP_404_NOT_FOUND)

    return produce_output(asset_type)


async def content_range_header_adder(
    repo: Annotated[AssetTypeRepository, Depends(asset_type_repository)],
) -> ContentRangeHeaderAdder[AssetType]:
    return ContentRangeHeaderAdder(repo, "asset-type")


@router.get(
    "/",
    name="asset-type:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(authenticate_user)],
)
async def list_asset_types(
    response: Response,
    content_range_header_adder: Annotated[ContentRangeHeaderAdder[AssetType], Depends(content_range_header_adder)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[AssetTypeListAction, Depends(asset_type_list_action)],
    produce_output: Annotated[AssetTypeOutputFactory, Depends(asset_type_output_factory)],
) -> list[AssetTypeOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    asset_types = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )

    await content_range_header_adder(response, pagination)

    return [produce_output(asset_type) for asset_type in asset_types]


@router.patch(
    "/{asset_type_id}",
    name="asset-type:update",
    responses={**unauthorized_response, **not_found_response, **conflict_response},
    dependencies=[Depends(authenticate_user)],
)
async def update_asset_type(
    input: AssetTypeUpdateInput,
    asset_type_id: Annotated[int, Path(description="The asset type id.", ge=1)],
    action: Annotated[AssetTypeUpdateAction, Depends(asset_type_update_action)],
    produce_output: Annotated[AssetTypeOutputFactory, Depends(asset_type_output_factory)],
) -> AssetTypeOutput:
    try:
        asset_type = await action(asset_type_id, input.model_dump(exclude_unset=True))
    except NotFoundException:
        raise HTTPException(HTTP_404_NOT_FOUND)

    return produce_output(asset_type)


@router.delete(
    "/{asset_type_id}",
    name="asset-type:delete",
    status_code=HTTP_204_NO_CONTENT,
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
async def delete_asset_type(
    asset_type_id: Annotated[int, Path(description="The asset type id.", ge=1)],
    action: Annotated[AssetTypeDeleteAction, Depends(asset_type_delete_action)],
) -> None:
    try:
        await action(asset_type_id)
    except NotFoundException:
        raise HTTPException(HTTP_404_NOT_FOUND)


@router.get(
    "/{asset_type_id}/wfs",
    name="asset-type:retrieve-wfs",
    responses={**unauthorized_response, **not_found_response},
    response_model=FeatureCollection,
)
async def retrieve_wfs(
    action: Annotated[WfsRetrieveAction, Depends(wfs_retrieve_action)],
    asset_type_id: Annotated[int, Path(description="The asset type id.", ge=1)],
    type_names: str = "app:container",
    count: int = 1000,
    srs_name: str = "urn:ogc:def:crs:EPSG::4326",
    output_format: Literal["application/json"] = "application/json",
    service: Literal["WFS"] = "WFS",
    version: str = "2.0.0",
    request: Literal["GetFeature"] = "GetFeature",
    filter: str | None = None,
) -> StreamingResponse:
    try:
        iterator = await action(
            asset_type_id, type_names, count, srs_name, output_format, service, version, request, filter
        )
    except NotFoundException as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e)) from e

    return StreamingResponse(iterator, media_type=output_format)
