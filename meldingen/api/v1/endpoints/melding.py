from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path
from meldingen_core.actions.melding import MeldingCreateAction

from meldingen.actions import MeldingListAction, MeldingRetrieveAction
from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Melding, MeldingCreateInput, MeldingOutput, User

router = APIRouter()


@router.post("/", name="melding:create")
@inject
async def create_melding(
    melding_input: MeldingCreateInput, action: MeldingCreateAction = Depends(Provide(Container.melding_create_action))
) -> MeldingOutput:
    melding = Melding(**melding_input.model_dump())
    await action(melding)

    output = MeldingOutput(id=melding.id, text=melding.text)

    return output


@router.get("/", name="melding:list")
@inject
async def list_meldingen(
    pagination: dict[str, int | None] = Depends(pagination_params),
    action: MeldingListAction = Depends(Provide(Container.melding_list_action)),
    user: User = Depends(authenticate_user),
) -> list[MeldingOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    meldingen = await action(limit=limit, offset=offset)
    output = []
    for melding in meldingen:
        output.append(MeldingOutput(id=melding.id, text=melding.text))

    return output


@router.get("/{melding_id}", name="melding:retrieve")
@inject
async def retrieve_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: MeldingRetrieveAction = Depends(Provide(Container.melding_retrieve_action)),
    user: User = Depends(authenticate_user),
) -> MeldingOutput:
    melding = await action(pk=melding_id)

    if not melding:
        raise HTTPException(status_code=404)

    return MeldingOutput(id=melding.id, text=melding.text)
