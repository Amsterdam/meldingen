from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions import FormIoPrimaryFormRetrieveAction
from meldingen.api.v1 import not_found_response
from meldingen.containers import Container
from meldingen.models import FormIoForm
from meldingen.schemas import FormComponentOutput, FormOutput

router = APIRouter()


async def _form_output_schema(form: FormIoForm) -> FormOutput:
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

    return await _form_output_schema(form=db_form)
