from meldingen.models import Melding
from meldingen.repositories import MeldingRepository


class AssetPurger:
    _repository: MeldingRepository

    def __init__(self, repository: MeldingRepository):
        self._repository = repository

    async def __call__(self, melding: Melding) -> None:
        try:

            await self._repository.delete_assets_from_melding(melding)
        except Exception as e:
            print(e)
