from typing import Any

from meldingen_core.actions.base import (
    BaseCreateAction,
    BaseCRUDAction,
    BaseDeleteAction,
    BaseListAction,
    BaseRetrieveAction,
    BaseUpdateAction,
)
from meldingen_core.actions.classification import ClassificationListAction as BaseClassificationListAction
from meldingen_core.actions.classification import ClassificationRetrieveAction as BaseClassificationRetrieveAction
from meldingen_core.actions.classification import ClassificationUpdateAction as BaseClassificationUpdateAction
from meldingen_core.actions.melding import MeldingListAction as BaseMeldingListAction
from meldingen_core.actions.melding import MeldingRetrieveAction as BaseMeldingRetrieveAction
from meldingen_core.actions.user import UserListAction as BaseUserListAction
from meldingen_core.actions.user import UserRetrieveAction as BaseUserRetrieveAction
from meldingen_core.actions.user import UserUpdateAction as BaseUserUpdateAction
from meldingen_core.exceptions import NotFoundException

from meldingen.models import (
    Classification,
    FormIoComponent,
    FormIoComponentTypeEnum,
    FormIoForm,
    FormIoPanelComponent,
    Melding,
    User,
)
from meldingen.repositories import FormIoFormRepository


class UserListAction(BaseUserListAction[User, User]): ...


class UserRetrieveAction(BaseUserRetrieveAction[User, User]): ...


class UserUpdateAction(BaseUserUpdateAction[User, User]): ...


class MeldingListAction(BaseMeldingListAction[Melding, Melding]): ...


class MeldingRetrieveAction(BaseMeldingRetrieveAction[Melding, Melding]): ...


class ClassificationListAction(BaseClassificationListAction[Classification, Classification]): ...


class ClassificationRetrieveAction(BaseClassificationRetrieveAction[Classification, Classification]): ...


class ClassificationUpdateAction(BaseClassificationUpdateAction[Classification, Classification]): ...


class FormIoComponentCreateAction(BaseCreateAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentUpdateAction(BaseUpdateAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentListAction(BaseListAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentRetrieveAction(BaseRetrieveAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentDeleteAction(BaseDeleteAction[FormIoComponent, FormIoComponent]): ...


class BaseFormIoFormCreateUpdateAction(BaseCRUDAction[FormIoForm, FormIoForm]):
    _repository: FormIoFormRepository

    async def _create_components(
        self, parent: FormIoForm | FormIoPanelComponent, components_values: list[dict[str, Any]]
    ) -> None:
        parent_components = await parent.awaitable_attrs.components
        parent_components.clear()

        for component_values in components_values:
            if component_values.get("type") == FormIoComponentTypeEnum.panel:
                child_components_values = component_values.pop("components", [])
                panel_component = FormIoPanelComponent(**component_values)

                await self._create_components(parent=panel_component, components_values=child_components_values)

                parent_components.append(panel_component)
            else:
                parent_components.append(FormIoComponent(**component_values))

        parent_components.reorder()


class FormIoFormCreateAction(BaseFormIoFormCreateUpdateAction):
    async def __call__(self, obj: FormIoForm, values: dict[str, Any]) -> None:
        component_values = values.pop("components", [])
        if component_values:
            await self._create_components(obj, component_values)
        await self._repository.save(obj)


class FormIoFormListAction(BaseListAction[FormIoForm, FormIoForm]): ...


class FormIoFormRetrieveAction(BaseRetrieveAction[FormIoForm, FormIoForm]): ...


class FormIoFormDeleteAction(BaseDeleteAction[FormIoForm, FormIoForm]): ...


class FormIoPrimaryFormRetrieveAction(BaseCRUDAction[FormIoForm, FormIoForm]):
    _repository: FormIoFormRepository

    async def __call__(self) -> FormIoForm | None:
        return await self._repository.retrieve_primary_form()


class BaseFormIoFormUpdateAction(BaseFormIoFormCreateUpdateAction):

    async def _update(self, obj: FormIoForm, values: dict[str, Any]) -> FormIoForm:
        component_values = values.pop("components", [])
        if component_values:
            await self._create_components(obj, component_values)

        for key, value in values.items():
            setattr(obj, key, value)

        await self._repository.save(obj)

        return obj


class FormIoFormUpdateAction(BaseFormIoFormUpdateAction):
    async def __call__(self, pk: int, values: dict[str, Any]) -> FormIoForm:
        obj = await self._repository.retrieve(pk=pk)
        if obj is None:
            raise NotFoundException()

        return await self._update(obj, values)


class FormIoPrimaryFormUpdateAction(BaseFormIoFormUpdateAction):
    async def __call__(self, values: dict[str, Any]) -> FormIoForm:
        obj = await self._repository.retrieve_primary_form()
        if obj is None:
            raise NotFoundException()

        return await self._update(obj, values)
