from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions import StaticFormRetrieveByTypeAction
from meldingen.api.v1 import not_found_response
from meldingen.containers import Container
from meldingen.models import StaticFormTypeEnum
from meldingen.schema_renderer import StaticFormOutPutRenderer
from meldingen.schemas import StaticFormOutput

router = APIRouter()


_hydrate_output = StaticFormOutPutRenderer()


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

    return await _hydrate_output(db_form)
