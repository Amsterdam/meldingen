from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException
from meldingen_core.actions.base import BaseCRUDAction, BaseDeleteAction, BaseRetrieveAction
from meldingen_core.exceptions import NotFoundException
from meldingen_core.token import TokenVerifier
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

from meldingen.actions.base import BaseListAction
from meldingen.exceptions import MeldingNotClassifiedException
from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator
from meldingen.models import (
    Answer,
    BaseFormIoValuesComponent,
    Form,
    FormIoCheckBoxComponent,
    FormIoComponentTypeEnum,
    FormIoComponentValue,
    FormIoPanelComponent,
    FormIoQuestionComponent,
    FormIoRadioComponent,
    FormIoSelectComponent,
    FormIoSelectComponentData,
    FormIoSelectComponentValue,
    FormIoTextAreaComponent,
    FormIoTextFieldComponent,
    Melding,
    Question,
    StaticForm,
)
from meldingen.repositories import (
    AnswerRepository,
    ClassificationRepository,
    FormIoQuestionComponentRepository,
    FormRepository,
    QuestionRepository,
    StaticFormRepository,
)
from meldingen.schemas.input import AnswerInput, FormComponent, FormInput, FormPanelComponentInput, StaticFormInput


class BaseFormCreateUpdateAction(BaseCRUDAction[Form]):
    _repository: FormRepository
    _question_repository: QuestionRepository

    def __init__(
        self,
        repository: FormRepository,
        question_repository: QuestionRepository,
    ) -> None:
        super().__init__(repository)
        self._question_repository = question_repository

    async def _create_question(self, component: FormIoQuestionComponent) -> None:
        form = await component.awaitable_attrs.form
        if form is None:
            parent = await component.awaitable_attrs.parent
            if parent is not None:
                form = await parent.awaitable_attrs.form

        if form is None:
            raise Exception("Failed to get form from component or parent!")

        question = Question(text=component.label, form=form)
        await self._question_repository.save(question, commit=False)

        component.question = question

    async def _create_component_values(
        self, component: BaseFormIoValuesComponent, values: list[dict[str, Any]]
    ) -> None:
        component_values = await component.awaitable_attrs.values

        for value in values:
            component_value = FormIoComponentValue(**value)
            component_values.append(component_value)

        component_values.reorder()

    async def _create_components(
        self, parent: Form | FormIoPanelComponent, components: Sequence[FormComponent]
    ) -> None:
        parent_components = await parent.awaitable_attrs.components
        parent_components.clear()

        for component in components:
            component_values = component.model_dump()

            if isinstance(component, FormPanelComponentInput):
                component_values.pop("components")

                panel_component = FormIoPanelComponent(**component_values)
                parent_components.append(panel_component)

                await self._create_components(parent=panel_component, components=component.components)
            else:
                value_data = component_values.pop("values", [])

                component_values.pop("validate_")

                if component.validate_ is not None:
                    if component.validate_.json_ is not None:
                        component_values["jsonlogic"] = component.validate_.json_.model_dump_json(by_alias=True)

                    if component.validate_.required is not None:
                        component_values["required"] = component.validate_.required
                        component_values["required_error_message"] = component.validate_.required_error_message

                if component_values.get("type") == FormIoComponentTypeEnum.checkbox:
                    c_component = FormIoCheckBoxComponent(**component_values)
                    await self._create_component_values(component=c_component, values=value_data)

                    parent_components.append(c_component)
                    await self._create_question(component=c_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.radio:
                    r_component = FormIoRadioComponent(**component_values)
                    await self._create_component_values(component=r_component, values=value_data)

                    parent_components.append(r_component)
                    await self._create_question(component=r_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.select:
                    data = component_values.pop("data")
                    assert data is not None

                    select_component = FormIoSelectComponent(**component_values)

                    select_component_data = FormIoSelectComponentData()
                    select_component_data_values = await select_component_data.awaitable_attrs.values

                    for value in data.get("values"):
                        component_value = FormIoSelectComponentValue(**value)
                        select_component_data_values.append(component_value)

                    select_component_data_values.reorder()

                    select_component.data = select_component_data

                    parent_components.append(select_component)
                    await self._create_question(select_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.text_area:
                    text_area_component = FormIoTextAreaComponent(**component_values)
                    parent_components.append(text_area_component)
                    await self._create_question(text_area_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.text_field:
                    text_field_component = FormIoTextFieldComponent(**component_values)
                    parent_components.append(text_field_component)
                    await self._create_question(text_field_component)
                else:
                    raise Exception(f"Unsupported component type: {component_values.get('type')}")

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

        form = Form(**dumped_form_input)
        form.classification = classification

        await self._create_components(form, form_input.components)
        await self._repository.save(form)

        return form


class FormListAction(BaseListAction[Form]): ...


class FormRetrieveAction(BaseRetrieveAction[Form]): ...


class FormDeleteAction(BaseDeleteAction[Form]): ...


class FormUpdateAction(BaseFormCreateUpdateAction):
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
                await self._repository.flush()
            except NotFoundException:
                """If the classification is not assigned to another form we do not need to take any action."""

        form_data = form_input.model_dump(exclude_unset=True, by_alias=True)
        form_data["classification"] = classification
        form_data.pop("components")

        for key, value in form_data.items():
            setattr(obj, key, value)

        await self._create_components(obj, form_input.components)
        await self._repository.save(obj)

        return obj


class FormRetrieveByClassificationAction(BaseCRUDAction[Form]):
    _repository: FormRepository

    async def __call__(self, classification_id: int) -> Form:
        try:
            return await self._repository.find_by_classification_id(classification_id)
        except NotFoundException:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)


class AnswerCreateAction(BaseCRUDAction[Answer]):
    _token_verifier: TokenVerifier[Melding]
    _question_repository: QuestionRepository
    _component_repository: FormIoQuestionComponentRepository
    _jsonlogic_validate: JSONLogicValidator

    def __init__(
        self,
        repository: AnswerRepository,
        token_verifier: TokenVerifier[Melding],
        question_repository: QuestionRepository,
        component_repository: FormIoQuestionComponentRepository,
        jsonlogic_validator: JSONLogicValidator,
    ):
        super().__init__(repository)
        self._token_verifier = token_verifier
        self._question_repository = question_repository
        self._component_repository = component_repository
        self._jsonlogic_validate = jsonlogic_validator

    async def __call__(self, melding_id: int, token: str, question_id: int, answer_input: AnswerInput) -> Answer:
        """
        Create and store an Answer in the database, subject to several conditions:

        Conditions:
        1. The melding must exist.
        2. The provided token must be valid.
        3. The melding must be classified.
        4. The question must exist.
        5. The question must belong to an existing and active form.
        """
        # Question must exist
        question = await self._question_repository.retrieve(question_id)
        if question is None:
            raise NotFoundException()

        # Token must valid
        melding = await self._token_verifier(melding_id, token)

        # Melding must be classified
        if not await melding.awaitable_attrs.classification:
            raise MeldingNotClassifiedException()

        # Question must belong to a form
        form = await question.awaitable_attrs.form
        if form is None:
            raise NotFoundException()

        # Store the answer
        answer_data = answer_input.model_dump(by_alias=True)
        form_component = await self._component_repository.find_component_by_question_id(question.id)
        if form_component.jsonlogic is not None:
            try:
                self._jsonlogic_validate(form_component.jsonlogic, answer_data)
            except JSONLogicValidationException as e:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=[{"msg": e.msg, "input": e.input}]
                ) from e

        answer = Answer(**answer_data, melding=melding, question=question)

        await self._repository.save(answer)

        return answer


class AnswerUpdateAction(BaseCRUDAction[Answer]):
    _token_verifier: TokenVerifier[Melding]
    _component_repository: FormIoQuestionComponentRepository
    _jsonlogic_validate: JSONLogicValidator

    def __init__(
        self,
        repository: AnswerRepository,
        token_verifier: TokenVerifier[Melding],
        component_repository: FormIoQuestionComponentRepository,
        jsonlogic_validator: JSONLogicValidator,
    ):
        super().__init__(repository)
        self._token_verifier = token_verifier
        self._component_repository = component_repository
        self._jsonlogic_validate = jsonlogic_validator

    async def __call__(self, melding_id: int, token: str, answer_id: int, text: str) -> Answer:
        melding = await self._token_verifier(melding_id, token)

        answer = await self._repository.retrieve(answer_id)
        if answer is None:
            raise NotFoundException("Answer not found")

        answer_melding = await answer.awaitable_attrs.melding
        if answer_melding != melding:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=[{"msg": "Answer does not belong to melding"}],
            )

        form_component = await self._component_repository.find_component_by_question_id(answer.question_id)
        if form_component.jsonlogic is not None:
            try:
                self._jsonlogic_validate(form_component.jsonlogic, {"text": text})
            except JSONLogicValidationException as e:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=[{"msg": e.msg, "input": e.input}]
                ) from e

        answer.text = text
        await self._repository.save(answer)

        return answer


class StaticFormRetrieveAction(BaseCRUDAction[StaticForm]):
    _repository: StaticFormRepository

    def __init__(self, repository: StaticFormRepository):
        super().__init__(repository)

    async def __call__(self, static_form_id: int) -> StaticForm | None:
        return await self._repository.retrieve(static_form_id)


class StaticFormUpdateAction(BaseCRUDAction[StaticForm]):
    _repository: StaticFormRepository

    async def _create_component_values(
        self, component: BaseFormIoValuesComponent, values: list[dict[str, Any]]
    ) -> None:
        component_values = await component.awaitable_attrs.values

        for value in values:
            component_value = FormIoComponentValue(**value)
            component_values.append(component_value)

        component_values.reorder()

    async def _create_components(
        self, parent: StaticForm | FormIoPanelComponent, components: Sequence[FormComponent]
    ) -> None:
        parent_components = await parent.awaitable_attrs.components
        parent_components.clear()

        for component in components:
            component_values = component.model_dump()

            if isinstance(component, FormPanelComponentInput):
                component_values.pop("components")
                panel_component = FormIoPanelComponent(**component_values)

                await self._create_components(parent=panel_component, components=component.components)

                parent_components.append(panel_component)
            else:
                value_data = component_values.pop("values", [])

                component_values.pop("validate_")

                if component.validate_ is not None:
                    if component.validate_.json_ is not None:
                        component_values["jsonlogic"] = component.validate_.json_.model_dump_json(by_alias=True)

                    if component.validate_.required is not None:
                        component_values["required"] = component.validate_.required

                if component_values.get("type") == FormIoComponentTypeEnum.checkbox:
                    c_component = FormIoCheckBoxComponent(**component_values)
                    await self._create_component_values(component=c_component, values=value_data)

                    parent_components.append(c_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.radio:
                    r_component = FormIoRadioComponent(**component_values)
                    await self._create_component_values(component=r_component, values=value_data)

                    parent_components.append(r_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.select:
                    data = component_values.pop("data")
                    assert data is not None

                    select_component = FormIoSelectComponent(**component_values)

                    select_component_data = FormIoSelectComponentData()
                    select_component_data_values = await select_component_data.awaitable_attrs.values

                    for value in data.get("values"):
                        component_value = FormIoSelectComponentValue(**value)
                        select_component_data_values.append(component_value)

                    select_component_data_values.reorder()

                    select_component.data = select_component_data

                    parent_components.append(select_component)
                elif component_values.get("type") == FormIoComponentTypeEnum.text_area:
                    parent_components.append(FormIoTextAreaComponent(**component_values))
                elif component_values.get("type") == FormIoComponentTypeEnum.text_field:
                    parent_components.append(FormIoTextFieldComponent(**component_values))
                else:
                    raise Exception(f"Unsupported component type: {component_values.get('type')}")

        parent_components.reorder()

    async def __call__(self, form_id: int, form_input: StaticFormInput) -> StaticForm:
        obj = await self._repository.retrieve(pk=form_id)

        if obj is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)

        form_data = form_input.model_dump(exclude_unset=True, by_alias=True)
        form_data.pop("components", [])

        for key, value in form_data.items():
            setattr(obj, key, value)

        await self._create_components(obj, form_input.components)
        await self._repository.save(obj)

        return obj


class StaticFormListAction(BaseListAction[StaticForm]): ...
