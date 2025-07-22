from sqlalchemy.orm.collections import InstrumentedList

from meldingen.models import Asset
from meldingen.repositories import AssetRepository


class AssetPurger:
    _repository: AssetRepository

    def __init__(self, repository: AssetRepository):
        self._repository = repository

    async def __call__(self, assets: InstrumentedList[Asset]) -> None:
        for asset in assets:
            await self._repository.delete(asset.id)
