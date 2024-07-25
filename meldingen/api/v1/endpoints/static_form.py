from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions import StaticFormRetrieveByTypeAction, StaticFormUpdateAction
from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import StaticFormTypeEnum, User
from meldingen.output_schemas import StaticFormOutput
from meldingen.schema_factories import StaticFormOutputFactory
from meldingen.schemas import StaticFormInput

router = APIRouter()


_output_factory = StaticFormOutputFactory()


@router.get("/{form_type}", name="static-form:retrieve-by-type", responses={**not_found_response})
@inject
async def retrieve_static_form(
    form_type: Annotated[StaticFormTypeEnum, Path(description="The type of the static form.")],
    action: StaticFormRetrieveByTypeAction = Depends(Provide(Container.static_form_retrieve_by_type_action)),
) -> StaticFormOutput:
    try:
        db_form = await action(form_type)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await _output_factory(db_form)


@router.put(
    "/{form_type}",
    name="static-form:update",
    responses={
        **unauthorized_response,
        **not_found_response,
    },
)
@inject
async def update_static_form(
    form_type: Annotated[StaticFormTypeEnum, Path(description="The type of the static form.")],
    form_input: StaticFormInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: StaticFormUpdateAction = Depends(Provide(Container.static_form_update_action)),
) -> StaticFormOutput:
    db_form = await action(form_type, form_input)

    return await _output_factory(db_form)
