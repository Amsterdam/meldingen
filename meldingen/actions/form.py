from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException
from meldingen_core.actions.base import BaseCRUDAction, BaseDeleteAction, BaseRetrieveAction
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from meldingen.actions.base import BaseListAction
from meldingen.models import (
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
    Question,
)
from meldingen.repositories import ClassificationRepository, FormRepository, QuestionRepository
from meldingen.schemas.input import FormComponent, FormInput, FormPanelComponentInput


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
