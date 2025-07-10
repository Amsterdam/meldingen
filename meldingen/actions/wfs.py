from meldingen_core.actions.wfs import WfsRetrieveAction as BaseWfsRetrieveAction

from meldingen.models import AssetType


class WfsRetrieveAction(BaseWfsRetrieveAction[AssetType]): ...
