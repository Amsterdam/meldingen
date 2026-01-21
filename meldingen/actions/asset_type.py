from meldingen_core.actions.asset_type import AssetTypeCreateAction as BaseAssetTypeCreateAction
from meldingen_core.actions.asset_type import AssetTypeDeleteAction as BaseAssetTypeDeleteAction
from meldingen_core.actions.asset_type import AssetTypeListAction as BaseAssetTypeListAction
from meldingen_core.actions.asset_type import AssetTypeRetrieveAction as BaseAssetTypeRetrieveAction
from meldingen_core.actions.asset_type import AssetTypeUpdateAction as BaseAssetTypeUpdateAction
from meldingen_core.actions.wfs import WfsRetrieveAction as BaseWfsRetrieveAction

from meldingen.actions.base import BaseListAction
from meldingen.models import AssetType


class AssetTypeCreateAction(BaseAssetTypeCreateAction[AssetType]): ...


class AssetTypeRetrieveAction(BaseAssetTypeRetrieveAction[AssetType]): ...


class AssetTypeListAction(BaseAssetTypeListAction[AssetType], BaseListAction[AssetType]): ...


class AssetTypeUpdateAction(BaseAssetTypeUpdateAction[AssetType]): ...


class AssetTypeDeleteAction(BaseAssetTypeDeleteAction[AssetType]): ...


class WfsRetrieveAction(BaseWfsRetrieveAction[AssetType]): ...
