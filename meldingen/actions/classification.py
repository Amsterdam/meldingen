from meldingen_core.actions.classification import ClassificationCreateAction as BaseClassificationCreateAction
from meldingen_core.actions.classification import ClassificationDeleteAction as BaseClassificationDeleteAction
from meldingen_core.actions.classification import ClassificationListAction as BaseClassificationListAction
from meldingen_core.actions.classification import ClassificationRetrieveAction as BaseClassificationRetrieveAction
from meldingen_core.actions.classification import ClassificationUpdateAction as BaseClassificationUpdateAction
from meldingen_core.repository_helpers import retrieve_or_raise_not_found

from meldingen.actions.base import BaseListAction
from meldingen.config import settings
from meldingen.models import AssetType, Classification
from meldingen.repositories import RepositoryListFilters


# Implementation specific exceptions and actions for classification management
class DefaultClassificationCannotBeDeleted(Exception):
    pass


class DefaultClassificationNameCannotBeUpdated(Exception):
    pass


class ClassificationListAction(
    BaseClassificationListAction[Classification, RepositoryListFilters], BaseListAction[Classification]
): ...


class ClassificationCreateAction(BaseClassificationCreateAction[Classification, AssetType]): ...


class ClassificationRetrieveAction(BaseClassificationRetrieveAction[Classification]): ...


class ClassificationUpdateAction(BaseClassificationUpdateAction[Classification, AssetType]):
    async def __call__(self, pk: int, update_payload: dict) -> Classification:
        classification = await retrieve_or_raise_not_found(self._repository, pk)

        if (
            classification.name == settings.llm_fallback_classification_name
            and update_payload.get("name") != classification.name
        ):
            raise DefaultClassificationNameCannotBeUpdated()

        return await super().__call__(pk, update_payload)


class ClassificationDeleteAction(BaseClassificationDeleteAction[Classification]):
    async def __call__(self, pk: int) -> None:
        classification = await retrieve_or_raise_not_found(self._repository, pk)

        if classification.name == settings.llm_fallback_classification_name:
            raise DefaultClassificationCannotBeDeleted()

        return await super().__call__(pk)
