from meldingen.repositories import MeldingRepository


class AssetPurger:
    _repository: MeldingRepository

    def __init__(self, repository: MeldingRepository):
        self._repository = repository

    async def __call__(self, melding_id: int) -> None:
        melding = await self._repository.retrieve(melding_id)

        assert melding is not None

        await self._repository.delete_assets_from_melding(melding)
