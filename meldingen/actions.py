from typing import Any, Collection, TypeVar, cast

from fastapi import HTTPException
from meldingen_core import SortingDirection
from meldingen_core.actions.attachment import UploadAttachmentAction as BaseUploadAttachmentAction
from meldingen_core.actions.base import BaseCRUDAction, BaseDeleteAction
from meldingen_core.actions.base import BaseListAction as BaseCoreListAction
from meldingen_core.actions.base import BaseRetrieveAction
from meldingen_core.actions.classification import ClassificationListAction as BaseClassificationListAction
from meldingen_core.actions.classification import ClassificationRetrieveAction as BaseClassificationRetrieveAction
from meldingen_core.actions.classification import ClassificationUpdateAction as BaseClassificationUpdateAction
from meldingen_core.actions.melding import MeldingListAction as BaseMeldingListAction
from meldingen_core.actions.melding import MeldingRetrieveAction as BaseMeldingRetrieveAction
from meldingen_core.actions.user import UserListAction as BaseUserListAction
from meldingen_core.actions.user import UserRetrieveAction as BaseUserRetrieveAction
from meldingen_core.actions.user import UserUpdateAction as BaseUserUpdateAction
from meldingen_core.exceptions import NotFoundException
from meldingen_core.token import TokenVerifier
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

from meldingen.exceptions import MeldingNotClassifiedException
from meldingen.models import (
    Answer,
    Classification,
    Form,
    FormIoCheckBoxComponent,
    FormIoComponent,
    FormIoComponentTypeEnum,
    FormIoComponentValue,
    FormIoPanelComponent,
    FormIoRadioComponent,
    Melding,
    Question,
    StaticForm,
    StaticFormTypeEnum,
    User,
)
from meldingen.repositories import (
    AnswerRepository,
    AttributeNotFoundException,
    ClassificationRepository,
    FormRepository,
    MeldingRepository,
    QuestionRepository,
    StaticFormRepository,
)
from meldingen.schemas import AnswerInput, FormInput, StaticFormInput

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class BaseListAction(BaseCoreListAction[T, T_co]):
    async def __call__(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Collection[T_co]:
        try:
            return await super().__call__(
                limit=limit, offset=offset, sort_attribute_name=sort_attribute_name, sort_direction=sort_direction
            )
        except AttributeNotFoundException as e:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_ENTITY,
                [{"loc": ("query", "sort"), "msg": e.message, "type": "attribute_not_found"}],
            )


class UserListAction(BaseUserListAction[User, User], BaseListAction[User, User]): ...


class UserRetrieveAction(BaseUserRetrieveAction[User, User]): ...


class UserUpdateAction(BaseUserUpdateAction[User, User]): ...


class MeldingListAction(BaseMeldingListAction[Melding, Melding], BaseListAction[Melding, Melding]): ...


class MeldingRetrieveAction(BaseMeldingRetrieveAction[Melding, Melding]): ...


class ClassificationListAction(
    BaseClassificationListAction[Classification, Classification], BaseListAction[Classification, Classification]
): ...


class ClassificationRetrieveAction(BaseClassificationRetrieveAction[Classification, Classification]): ...


class ClassificationUpdateAction(BaseClassificationUpdateAction[Classification, Classification]): ...


class BaseFormCreateUpdateAction(BaseCRUDAction[Form, Form]):
    _repository: FormRepository
    _question_repository: QuestionRepository

    def __init__(
        self,
        repository: FormRepository,
        question_repository: QuestionRepository,
    ) -> None:
        super().__init__(repository)
        self._question_repository = question_repository

    async def _create_question(self, component: FormIoComponent) -> None:
        """
        A question will only be created if:
            - A panel component is NOT a decorative component
            - A component must be part of a form
        """
        if component.type == FormIoComponentTypeEnum.panel or not component.form:
            return

        # If the question already exists use the one from the database
        question = await self._question_repository.retrieve_by_text_and_form_id(
            text=component.label, form_id=component.form.id
        )
        if not question:
            question = Question(text=component.label, form=component.form)
            await self._question_repository.save(question, commit=False)

        component.question = question

    async def _create_component_values(
        self, component: FormIoRadioComponent | FormIoCheckBoxComponent, values: list[dict[str, Any]]
    ) -> FormIoRadioComponent | FormIoCheckBoxComponent:
        component_values = await component.awaitable_attrs.values

        for value in values:
            component_value = FormIoComponentValue(**value)
            component_values.append(component_value)

        component_values.reorder()
        return component

    async def _create_components(
        self, parent: Form | FormIoPanelComponent, components_values: list[dict[str, Any]]
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
                value_data = component_values.pop("values", [])

                if component_values.get("type") == FormIoComponentTypeEnum.checkbox:
                    c_component = FormIoCheckBoxComponent(**component_values)
                    _c_component = await self._create_component_values(component=c_component, values=value_data)
                    c_component = cast(FormIoCheckBoxComponent, _c_component)  # Needed for mypy

                    parent_components.append(c_component)
                    await self._create_question(component=c_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.radio:
                    r_component = FormIoRadioComponent(**component_values)
                    _r_component = await self._create_component_values(component=r_component, values=value_data)
                    r_component = cast(FormIoRadioComponent, _r_component)  # Needed for mypy

                    parent_components.append(r_component)
                    await self._create_question(component=r_component)
                else:
                    component = FormIoComponent(**component_values)
                    parent_components.append(component)
                    await self._create_question(component=component)

        parent_components.reorder()


class FormCreateAction(BaseFormCreateUpdateAction):
    _classification_repository: ClassificationRepository

    def __init__(
        self,
        repository: FormRepository,
        classification_repository: ClassificationRepository,
        question_repository: QuestionRepository,
    ):
        super().__init__(repository, question_repository)
        self._classification_repository = classification_repository

    async def __call__(self, form_input: FormInput) -> Form:
        classification = None
        if form_input.classification is not None:
            classification = await self._classification_repository.retrieve(form_input.classification)
            if classification is None:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Classification not found")

        dumped_form_input = form_input.model_dump(by_alias=True)
        dumped_form_input.pop("components")

        dumped_components_input = []
        for component in form_input.components:
            dumped_components_input.append(component.model_dump())

        form = Form(**dumped_form_input)
        form.classification = classification

        await self._create_components(form, dumped_components_input)
        await self._repository.save(form)

        return form


class FormListAction(BaseListAction[Form, Form]): ...


class FormRetrieveAction(BaseRetrieveAction[Form, Form]): ...


class FormDeleteAction(BaseDeleteAction[Form, Form]): ...


class BaseFormUpdateAction(BaseFormCreateUpdateAction):
    async def _update(self, obj: Form, values: dict[str, Any]) -> Form:
        component_values = values.pop("components", [])
        if component_values:
            await self._create_components(obj, component_values)

        for key, value in values.items():
            setattr(obj, key, value)

        await self._repository.save(obj)

        return obj


class FormUpdateAction(BaseFormUpdateAction):
    _classification_repository: ClassificationRepository

    def __init__(
        self,
        repository: FormRepository,
        classification_repository: ClassificationRepository,
        question_repository: QuestionRepository,
    ):
        super().__init__(repository, question_repository)
        self._classification_repository = classification_repository

    async def __call__(self, pk: int, form_input: FormInput) -> Form:
        obj = await self._repository.retrieve(pk=pk)
        if obj is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)

        classification = None
        if form_input.classification is not None:
            classification = await self._classification_repository.retrieve(form_input.classification)
            if classification is None:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Classification not found")

            try:
                other_form = await self._repository.find_by_classification_id(form_input.classification)
                other_form.classification = None
                await self._repository.save(other_form, commit=False)
            except NotFoundException:
                """If the classification is not assigned to another form we do not need to take any action."""

        form_data = form_input.model_dump(exclude_unset=True, by_alias=True)
        form_data["classification"] = classification
        form_data.pop("components")
        components = []
        for component in form_input.components:
            components.append(component.model_dump())
        form_data["components"] = components

        return await self._update(obj, form_data)


class FormRetrieveByClassificationAction(BaseCRUDAction[Form, Form]):
    _repository: FormRepository

    async def __call__(self, classification_id: int) -> Form:
        try:
            return await self._repository.find_by_classification_id(classification_id)
        except NotFoundException:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)


class AnswerCreateAction(BaseCRUDAction[Answer, Answer]):
    _token_verifier: TokenVerifier[Melding]
    _melding_repository: MeldingRepository
    _question_repository: QuestionRepository

    def __init__(
        self,
        repository: AnswerRepository,
        token_verifier: TokenVerifier[Melding],
        melding_repository: MeldingRepository,
        question_repository: QuestionRepository,
    ):
        super().__init__(repository)
        self._token_verifier = token_verifier
        self._melding_repository = melding_repository
        self._question_repository = question_repository

    async def __call__(self, melding_id: int, token: str, question_id: int, answer_input: AnswerInput) -> Answer:
        """
        Create and store an Answer in the database, subject to several conditions:

        Conditions:
        1. The melding must exist.
        2. The provided token must be valid.
        3. The melding must be classified.
        4. The question must exist.
        5. The question must belong to an existing and active form.

        TODO: Validate the answer against the rules stored in the component (using JSONLogic?).
        """
        # Question must exist
        question = await self._question_repository.retrieve(question_id)
        if question is None:
            raise NotFoundException()

        # Melding must exist
        melding = await self._melding_repository.retrieve(melding_id)
        if melding is None:
            raise NotFoundException()

        # Token must valid
        self._token_verifier(melding, token)

        # Melding must be classified
        if not melding.classification:
            raise MeldingNotClassifiedException()

        # Question must belong to a form
        form = await question.awaitable_attrs.form
        if form is None:
            raise NotFoundException()

        # Store the answer
        # TODO: Add validation (using JSONLogic?)
        answer_data = answer_input.model_dump(by_alias=True)

        answer = Answer(**answer_data, melding=melding, question=question)

        await self._repository.save(answer)

        return answer


class StaticFormRetrieveByTypeAction(BaseCRUDAction[StaticForm, StaticForm]):
    _repository: StaticFormRepository

    def __init__(self, repository: StaticFormRepository):
        super().__init__(repository)

    async def __call__(self, form_type: StaticFormTypeEnum) -> StaticForm:
        return await self._repository.retrieve_by_type(form_type)


class StaticFormUpdateAction(BaseCRUDAction[StaticForm, StaticForm]):
    _repository: StaticFormRepository

    async def _create_component_values(
        self, component: FormIoRadioComponent | FormIoCheckBoxComponent, values: list[dict[str, Any]]
    ) -> FormIoRadioComponent | FormIoCheckBoxComponent:
        component_values = await component.awaitable_attrs.values

        for value in values:
            component_value = FormIoComponentValue(**value)
            component_values.append(component_value)

        component_values.reorder()
        return component

    async def _create_components(
        self, parent: StaticForm | FormIoPanelComponent, components_values: list[dict[str, Any]]
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
                value_data = component_values.pop("values", [])

                if component_values.get("type") == FormIoComponentTypeEnum.checkbox:
                    c_component = FormIoCheckBoxComponent(**component_values)
                    _c_component = await self._create_component_values(component=c_component, values=value_data)
                    c_component = cast(FormIoCheckBoxComponent, _c_component)  # Needed for mypy

                    parent_components.append(c_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.radio:
                    r_component = FormIoRadioComponent(**component_values)
                    _r_component = await self._create_component_values(component=r_component, values=value_data)
                    r_component = cast(FormIoRadioComponent, _r_component)  # Needed for mypy

                    parent_components.append(r_component)
                else:
                    component = FormIoComponent(**component_values)
                    parent_components.append(component)

        parent_components.reorder()

    async def __call__(self, form_type: StaticFormTypeEnum, form_input: StaticFormInput) -> StaticForm:
        try:
            obj = await self._repository.retrieve_by_type(form_type=form_type)
        except NotFoundException:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)

        form_data = form_input.model_dump(exclude_unset=True, by_alias=True)
        form_data.pop("components", [])

        for key, value in form_data.items():
            setattr(obj, key, value)

        form_component_data = []
        for component in form_input.components:
            form_component_data.append(component.model_dump())

        if form_component_data:
            await self._create_components(obj, form_component_data)

        await self._repository.save(obj)

        return obj


class UploadAttachmentAction(BaseUploadAttachmentAction[Melding, Melding]): ...
