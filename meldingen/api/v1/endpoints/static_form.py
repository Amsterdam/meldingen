from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions import StaticFormListAction, StaticFormRetrieveAction, StaticFormUpdateAction
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import (
    simple_static_form_output_factory,
    static_form_list_action,
    static_form_output_factory,
    static_form_repository,
    static_form_retrieve_action,
    static_form_update_action,
)
from meldingen.repositories import StaticFormRepository
from meldingen.schemas.input import StaticFormInput
from meldingen.schemas.output import SimpleStaticFormOutput, StaticFormOutput
from meldingen.schemas.output_factories import SimpleStaticFormOutputFactory, StaticFormOutputFactory

router = APIRouter()


async def _add_content_range_header(
    response: Response,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    repo: Annotated[StaticFormRepository, Depends(static_form_repository)],
) -> None:
    await ContentRangeHeaderAdder(repo, "StaticForm")(response, pagination)


@router.get("/{static_form_id}", name="static-form:retrieve", responses={**not_found_response})
async def retrieve_static_form(
    static_form_id: Annotated[int, Path(description="The id of the static form.", ge=1)],
    action: Annotated[StaticFormRetrieveAction, Depends(static_form_retrieve_action)],
    produce_output_model: Annotated[StaticFormOutputFactory, Depends(static_form_output_factory)],
) -> StaticFormOutput:
    db_form = await action(static_form_id)

    if db_form is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await produce_output_model(db_form)


@router.put(
    "/{static_form_id}",
    name="static-form:update",
    responses={
        **unauthorized_response,
        **not_found_response,
    },
    dependencies=[Depends(authenticate_user)],
)
async def update_static_form(
    static_form_id: Annotated[int, Path(description="The id of the static form.", ge=1)],
    form_input: StaticFormInput,
    action: Annotated[StaticFormUpdateAction, Depends(static_form_update_action)],
    produce_output_model: Annotated[StaticFormOutputFactory, Depends(static_form_output_factory)],
) -> StaticFormOutput:
    db_form = await action(static_form_id, form_input)

    return await produce_output_model(db_form)


@router.get(
    "/",
    name="static-form:list",
    responses={**not_found_response},
    dependencies=[Depends(_add_content_range_header)],
)
async def list_static_forms(
    action: Annotated[StaticFormListAction, Depends(static_form_list_action)],
    produce_output_model: Annotated[SimpleStaticFormOutputFactory, Depends(simple_static_form_output_factory)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
) -> list[SimpleStaticFormOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    forms = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )

    return [await produce_output_model(db_form) for db_form in forms]
