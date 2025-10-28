from meldingen_core.actions.asset import ListAssetsAction as BaseListAssetsAction
from meldingen_core.actions.asset import MelderListAssetsAction as BaseMelderListAssetsAction

from meldingen.models import Asset, Melding


class ListAssetsAction(BaseListAssetsAction[Asset, Melding]): ...


class MelderListAssetsAction(BaseMelderListAssetsAction[Asset, Melding]): ...
