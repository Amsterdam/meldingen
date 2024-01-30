from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from meldingen.containers import Container
from meldingen.models import Melding
from meldingen.repositories import MeldingRepository

router = APIRouter()


@router.post("/", response_model=Melding)
@inject
async def create_melding(
    melding: Melding, melding_repository: MeldingRepository = Depends(Provide(Container.melding_repository))
) -> Melding:
    melding_repository.add(melding)

    return melding
