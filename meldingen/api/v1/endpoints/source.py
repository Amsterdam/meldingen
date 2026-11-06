from typing import Annotated

from fastapi import APIRouter, Depends, Response

from meldingen.actions.source import SourceListAction
from meldingen.api.utils import (
    ContentRangeHeaderAdder,
    PaginationParams,
    SortParams,
    pagination_params,
    sort_param,
)
from meldingen.api.v1 import list_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import list_filters, source_list_action, source_output_factory, source_repository
from meldingen.models import Source
from meldingen.repositories import RepositoryListFilters, SourceRepository
from meldingen.schemas.output import SourceOutput
from meldingen.schemas.output_factories import SourceOutputFactory

router = APIRouter()


async def content_range_header_adder(
    repo: Annotated[SourceRepository, Depends(source_repository)],
) -> ContentRangeHeaderAdder[Source]:
    return ContentRangeHeaderAdder(repo, "source")


@router.get(
    "/",
    name="source:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(authenticate_user)],
)
async def list_sources(
    response: Response,
    content_range_header_adder: Annotated[ContentRangeHeaderAdder[Source], Depends(content_range_header_adder)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[SourceListAction, Depends(source_list_action)],
    produce_output: Annotated[SourceOutputFactory, Depends(source_output_factory)],
    list_filters: Annotated[RepositoryListFilters | None, Depends(list_filters)],
) -> list[SourceOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    sources = await action(
        limit=limit,
        offset=offset,
        sort_attribute_name=sort.get_attribute_name(),
        sort_direction=sort.get_direction(),
        filters=list_filters,
    )

    await content_range_header_adder(response, pagination, list_filters)

    return [produce_output(source) for source in sources]
