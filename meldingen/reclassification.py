from meldingen_core.reclassification import BaseReclassification
from sqlalchemy.orm.collections import InstrumentedList

from meldingen.answer import AnswerPurger
from meldingen.asset import AssetPurger
from meldingen.location import LocationPurger
from meldingen.models import Asset, Classification, Melding


class Reclassifier(BaseReclassification[Melding, Classification]):
    _purge_answers: AnswerPurger
    _purge_location: LocationPurger
    _purge_assets: AssetPurger

    def __init__(self, answer_purger: AnswerPurger, location_purger: LocationPurger, asset_purger: AssetPurger) -> None:
        self._purge_answers = answer_purger
        self._purge_location = location_purger
        self._purge_assets = asset_purger

    async def __call__(self, melding: Melding, new_classification: Classification | None) -> None:
        old_classification: Classification | None = await melding.awaitable_attrs.classification
        assets: InstrumentedList[Asset] = await melding.awaitable_attrs.assets

        # New classification is the same: no need to purge anything
        if old_classification == new_classification:
            return

        # Always purge answers if the classification changed
        await self._purge_answers(melding.id)

        old_asset_type = await old_classification.awaitable_attrs.asset_type if old_classification else None
        new_asset_type = await new_classification.awaitable_attrs.asset_type if new_classification else None

        if old_asset_type == new_asset_type:
            return

        # Always purge assets if the asset type changed
        await self._purge_assets(assets)

        # Location is not compatible when assets need to be selected
        if new_asset_type:
            await self._purge_location(melding.id)
