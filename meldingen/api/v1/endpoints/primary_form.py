from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions import FormIoPrimaryFormRetrieveAction, FormIoPrimaryFormUpdateAction
from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import FormIoForm, User
from meldingen.schemas import FormComponentOutput, FormOutput, FormUpdateInput

router = APIRouter()


async def _hydrate_output(form: FormIoForm) -> FormOutput:
    components_output = [
        FormComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=component.auto_expand,
            show_char_count=component.show_char_count,
            position=component.position,
        )
        for component in await form.awaitable_attrs.components
    ]

    return FormOutput(title=form.title, display=form.display, components=components_output)


@router.get("/", name="primary-form:retrieve", responses={**not_found_response})
@inject
async def retrieve_primary_form(
    action: FormIoPrimaryFormRetrieveAction = Depends(Provide(Container.primary_form_retrieve_action)),
) -> FormOutput:
    """The primary form that is used to initiate the creation of a "Melding"."""
    db_form = await action()

    if not db_form:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await _hydrate_output(form=db_form)


@router.put("/", name="primary-form:update", responses={**unauthorized_response, **not_found_response})
@inject
async def update_primary_form(
    form_input: FormUpdateInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: FormIoPrimaryFormUpdateAction = Depends(Provide(Container.primary_form_update_action)),
) -> FormOutput:
    """Update the primary form that is used to initiate the creation of a "Melding"."""
    form_data = form_input.model_dump(exclude_unset=True)

    try:
        db_form = await action(form_data)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await _hydrate_output(form=db_form)
