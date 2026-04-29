from typing import Annotated

from fastapi import APIRouter, Depends, Response
from meldingen_core.filters import NameListFilters
from sqlalchemy import ColumnExpressionArgument

from meldingen.actions.label import LabelListAction
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
from meldingen.dependencies import label_list_action, label_output_factory, label_repository
from meldingen.models import Label
from meldingen.repositories import LabelRepository
from meldingen.schemas.output import LabelOutput
from meldingen.schemas.output_factories import LabelOutputFactory

router = APIRouter()


async def content_range_header_adder(
    repo: Annotated[LabelRepository, Depends(label_repository)],
) -> ContentRangeHeaderAdder[Label]:
    return ContentRangeHeaderAdder(repo, "label")


@router.get(
    "/",
    name="label:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(authenticate_user)],
)
async def list_labels(
    response: Response,
    content_range_header_adder: Annotated[ContentRangeHeaderAdder[Label], Depends(content_range_header_adder)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[LabelListAction, Depends(label_list_action)],
    produce_output: Annotated[LabelOutputFactory, Depends(label_output_factory)],
    filter_params: Annotated[FilterParams, Depends(filter_param)],
) -> list[LabelOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0
    q = filter_params.q

    labels = await action(
        limit=limit,
        offset=offset,
        sort_attribute_name=sort.get_attribute_name(),
        sort_direction=sort.get_direction(),
        filters=NameListFilters(name_contains=q) if q is not None else None,
    )

    content_range_filters: list[ColumnExpressionArgument[bool]] | None = (
        [Label.name.ilike(f"%{q}%")] if q is not None else None
    )
    await content_range_header_adder(response, pagination, content_range_filters)

    return [produce_output(label) for label in labels]
