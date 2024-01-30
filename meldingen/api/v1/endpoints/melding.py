from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from meldingen_core.actions import MeldingCreateAction

from meldingen.containers import Container
from meldingen.models import Melding

router = APIRouter()


@router.post("/", response_model=Melding)
@inject
async def create_melding(
    melding: Melding, action: MeldingCreateAction = Depends(Provide(Container.melding_create_action))
) -> Melding:
    action(melding)

    return melding
