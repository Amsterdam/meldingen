from typing import Annotated

from fastapi import APIRouter, Depends, Response
from meldingen_core.filters import NameListFilters
from sqlalchemy import ColumnExpressionArgument

from meldingen.actions.source import SourceListAction
from meldingen.api.utils import (
    ContentRangeHeaderAdder,
    FilterParams,
    PaginationParams,
    SortParams,
    filter_param,
    pagination_params,
    sort_param,
)
from meldingen.api.v1 import list_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import source_list_action, source_output_factory, source_repository
from meldingen.models import Source
from meldingen.repositories import SourceRepository
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
    filter_params: Annotated[FilterParams, Depends(filter_param)],
) -> list[SourceOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0
    q = filter_params.q

    sources = await action(
        limit=limit,
        offset=offset,
        sort_attribute_name=sort.get_attribute_name(),
        sort_direction=sort.get_direction(),
        filters=NameListFilters(name_contains=q) if q is not None else None,
    )

    content_range_filters: list[ColumnExpressionArgument[bool]] | None = (
        [Source.name.ilike(f"%{q}%")] if q is not None else None
    )
    await content_range_header_adder(response, pagination, content_range_filters)

    return [produce_output(source) for source in sources]
