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

from meldingen.models import Classification, FormIoComponent, FormIoForm, Melding, User
from meldingen.repositories import FormIoFormRepository


class UserListAction(BaseUserListAction[User, User]): ...


class UserRetrieveAction(BaseUserRetrieveAction[User, User]): ...


class UserUpdateAction(BaseUserUpdateAction[User, User]): ...


class MeldingListAction(BaseMeldingListAction[Melding, Melding]): ...


class MeldingRetrieveAction(BaseMeldingRetrieveAction[Melding, Melding]): ...


class ClassificationListAction(BaseClassificationListAction[Classification, Classification]): ...


class ClassificationRetrieveAction(BaseClassificationRetrieveAction[Classification, Classification]): ...


class ClassificationUpdateAction(BaseClassificationUpdateAction[Classification, Classification]): ...


class FormIoFormCreateAction(BaseCreateAction[FormIoForm, FormIoForm]): ...


class FormIoFormUpdateAction(BaseUpdateAction[FormIoForm, FormIoForm]): ...


class FormIoFormListAction(BaseListAction[FormIoForm, FormIoForm]): ...


class FormIoFormRetrieveAction(BaseRetrieveAction[FormIoForm, FormIoForm]): ...


class FormIoFormDeleteAction(BaseDeleteAction[FormIoForm, FormIoForm]): ...


class FormIoComponentCreateAction(BaseCreateAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentUpdateAction(BaseUpdateAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentListAction(BaseListAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentRetrieveAction(BaseRetrieveAction[FormIoComponent, FormIoComponent]): ...


class FormIoComponentDeleteAction(BaseDeleteAction[FormIoComponent, FormIoComponent]): ...


class FormIoPrimaryFormRetrieveAction(BaseCRUDAction[FormIoForm, FormIoForm]):
    _repository: FormIoFormRepository

    async def __call__(self) -> FormIoForm | None:
        return await self._repository.retrieve_primary_form()


class FormIoPrimaryFormUpdateAction(BaseCRUDAction[FormIoForm, FormIoForm]):
    _repository: FormIoFormRepository

    async def __call__(self, values: dict[str, Any]) -> FormIoForm:
        _form = await self._repository.retrieve_primary_form()
        if _form is None:
            raise NotFoundException()

        await self._repository.delete_components(pk=_form.id)

        form_components = await _form.awaitable_attrs.components
        for component_values in values.pop("components", []):
            FormIoComponent(form=_form, **component_values)
        form_components.reorder()

        for key, value in values.items():
            setattr(_form, key, value)

        await self._repository.save(_form)

        return _form
