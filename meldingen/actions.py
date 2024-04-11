from typing import Any, override

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
    async def _create_components(
        self, values: list[dict[str, Any]], form: FormIoForm | None = None, parent: FormIoPanelComponent | None = None
    ) -> None:
        for component_values in values:
            component_components_values = component_values.pop("components", [])
            if component_values.get("type") == FormIoComponentTypeEnum.panel:
                panel_component = FormIoPanelComponent(form=form, parent=parent, **component_values)

                panel_components = await panel_component.awaitable_attrs.components

                await self._create_components(component_components_values, form=None, parent=panel_component)

                panel_components.reorder()
            else:
                FormIoComponent(**component_values, form=form, parent=parent)


class FormIoFormCreateAction(BaseFormIoFormCreateUpdateAction):
    async def __call__(self, obj: FormIoForm, values: list[dict[str, Any]]) -> None:
        form_components = await obj.awaitable_attrs.components
        await self._create_components(values, form=obj, parent=None)
        form_components.reorder()

        await self._repository.save(obj)


class FormIoFormListAction(BaseListAction[FormIoForm, FormIoForm]): ...


class FormIoFormRetrieveAction(BaseRetrieveAction[FormIoForm, FormIoForm]): ...


class FormIoFormDeleteAction(BaseDeleteAction[FormIoForm, FormIoForm]): ...


class FormIoPrimaryFormRetrieveAction(BaseCRUDAction[FormIoForm, FormIoForm]):
    _repository: FormIoFormRepository

    async def __call__(self) -> FormIoForm | None:
        return await self._repository.retrieve_primary_form()


class BaseFormIoFormUpdateAction(BaseFormIoFormCreateUpdateAction):
    _repository: FormIoFormRepository

    async def _delete_components(self, form: FormIoForm) -> None:
        await self._repository.delete_components(pk=form.id)

    async def _update(self, form: FormIoForm, values: dict[str, Any]) -> FormIoForm:
        await self._delete_components(form)

        form_components = await form.awaitable_attrs.components

        await self._create_components(values.pop("components", []), form=form, parent=None)

        form_components.reorder()

        for key, value in values.items():
            setattr(form, key, value)

        await self._repository.save(form)

        return form


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
