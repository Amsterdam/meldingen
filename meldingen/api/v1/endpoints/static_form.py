from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions import StaticFormListAction, StaticFormRetrieveByTypeAction, StaticFormUpdateAction
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import (
    static_form_list_action,
    static_form_output_factory,
    static_form_repository,
    static_form_retrieve_by_type_action,
    static_form_update_action,
)
from meldingen.models import StaticFormTypeEnum
from meldingen.output_schemas import StaticFormOutput
from meldingen.repositories import StaticFormRepository
from meldingen.schema_factories import StaticFormOutputFactory
from meldingen.schemas import StaticFormInput

router = APIRouter()


async def _add_content_range_header(
    response: Response,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    repo: Annotated[StaticFormRepository, Depends(static_form_repository)],
) -> None:
    await ContentRangeHeaderAdder(repo, "StaticForm")(response, pagination)


@router.get("/{form_type}", name="static-form:retrieve-by-type", responses={**not_found_response})
async def retrieve_static_form(
    form_type: Annotated[StaticFormTypeEnum, Path(description="The type of the static form.")],
    action: Annotated[StaticFormRetrieveByTypeAction, Depends(static_form_retrieve_by_type_action)],
    produce_output_model: Annotated[StaticFormOutputFactory, Depends(static_form_output_factory)],
) -> StaticFormOutput:
    try:
        db_form = await action(form_type)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await produce_output_model(db_form)


@router.put(
    "/{form_type}",
    name="static-form:update",
    responses={
        **unauthorized_response,
        **not_found_response,
    },
    dependencies=[Depends(authenticate_user)],
)
async def update_static_form(
    form_type: Annotated[StaticFormTypeEnum, Path(description="The type of the static form.")],
    form_input: StaticFormInput,
    action: Annotated[StaticFormUpdateAction, Depends(static_form_update_action)],
    produce_output_model: Annotated[StaticFormOutputFactory, Depends(static_form_output_factory)],
) -> StaticFormOutput:
    db_form = await action(form_type, form_input)

    return await produce_output_model(db_form)


@router.get(
    "/",
    name="static-form:list",
    responses={**not_found_response},
    dependencies=[Depends(_add_content_range_header)],
)
async def list_static_forms(
    action: Annotated[StaticFormListAction, Depends(static_form_list_action)],
    produce_output_model: Annotated[StaticFormOutputFactory, Depends(static_form_output_factory)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
) -> list[StaticFormOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    forms = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )

    return [await produce_output_model(db_form) for db_form in forms]
