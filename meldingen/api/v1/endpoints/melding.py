from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from meldingen_core.actions import MeldingCreateAction

from meldingen.containers import Container
from meldingen.models import Melding, MeldingCreateInput

router = APIRouter()


@router.post("/")
@inject
async def create_melding(
    melding_input: MeldingCreateInput, action: MeldingCreateAction = Depends(Provide(Container.melding_create_action))
) -> Melding:
    melding = Melding(**melding_input.model_dump())
    action(melding)

    return melding
