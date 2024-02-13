from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from meldingen_core.actions import MeldingCreateAction, MeldingListAction, MeldingRetrieveAction

from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Melding, MeldingCreateInput, User

router = APIRouter()


@router.post("/", name="melding:create")
@inject
async def create_melding(
    melding_input: MeldingCreateInput, action: MeldingCreateAction = Depends(Provide(Container.melding_create_action))
) -> Melding:
    melding = Melding.model_validate(melding_input)
    action(melding)

    return melding


@router.get("/", name="melding:list", response_model=list[Melding])
@inject
async def list_meldingen(
    pagination: dict[str, int | None] = Depends(pagination_params),
    action: MeldingListAction = Depends(Provide(Container.melding_list_action)),
    user: User = Depends(authenticate_user),
) -> Any:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    meldingen = await action(limit=limit, offset=offset)

    return meldingen


@router.get("/{melding_id}", name="melding:retrieve", response_model=Melding)
@inject
async def retrieve_melding(
    melding_id: int,
    action: MeldingRetrieveAction = Depends(Provide(Container.melding_retrieve_action)),
    user: User = Depends(authenticate_user),
) -> Any:
    melding = await action(pk=melding_id)

    if not melding:
        raise HTTPException(status_code=404)

    return melding
