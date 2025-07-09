from meldingen_core.actions.classification import ClassificationCreateAction as BaseClassificationCreateAction
from meldingen_core.actions.classification import ClassificationDeleteAction as BaseClassificationDeleteAction
from meldingen_core.actions.classification import ClassificationListAction as BaseClassificationListAction
from meldingen_core.actions.classification import ClassificationRetrieveAction as BaseClassificationRetrieveAction
from meldingen_core.actions.classification import ClassificationUpdateAction as BaseClassificationUpdateAction

from meldingen.actions.base import BaseListAction
from meldingen.models import AssetType, Classification


class ClassificationListAction(BaseClassificationListAction[Classification], BaseListAction[Classification]): ...


class ClassificationCreateAction(BaseClassificationCreateAction[Classification, AssetType]): ...


class ClassificationRetrieveAction(BaseClassificationRetrieveAction[Classification]): ...


class ClassificationUpdateAction(BaseClassificationUpdateAction[Classification, AssetType]): ...


class ClassificationDeleteAction(BaseClassificationDeleteAction[Classification]): ...
