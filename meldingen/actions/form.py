from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException
from meldingen_core.actions.base import BaseCRUDAction, BaseDeleteAction, BaseRetrieveAction
from meldingen_core.exceptions import NotFoundException
from meldingen_core.token import TokenVerifier
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_CONTENT

from meldingen.actions.base import BaseListAction
from meldingen.exceptions import MeldingNotClassifiedException
from meldingen.factories import AnswerFactory, FormIoQuestionComponentFactory
from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator
from meldingen.models import (
    Answer,
    BaseFormIoValuesComponent,
    Form,
    FormIoCheckBoxComponent,
    FormIoComponent,
    FormIoComponentToAnswerTypeMap,
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
from meldingen.schemas.input import (
    AnswerInputUnion,
    FormComponentInputValidate,
    FormComponentUnion,
    FormInput,
    FormPanelComponentInput,
    StaticFormInput,
    TextAnswerInput,
)


class BaseFormCreateUpdateAction(BaseCRUDAction[Form]):
    _repository: FormRepository
    _question_repository: QuestionRepository
    _produce_question_component: FormIoQuestionComponentFactory

    def __init__(
        self,
        repository: FormRepository,
        question_repository: QuestionRepository,
        form_io_question_component_factory: FormIoQuestionComponentFactory,
    ) -> None:
        super().__init__(repository)
        self._question_repository = question_repository
        self._produce_question_component = form_io_question_component_factory

    async def _sync_component_tree(
        self, parent: Form | FormIoPanelComponent, input_components: Sequence[FormComponentUnion]
    ) -> None:
        """This method syncs the component tree of a Form or FormIoPanelComponent with the given input components.
        It updates existing components, creates new components and deletes removed components based on the unique FormIO keys.
        The order of the components is also updated to match the input list."""
        parent_components = await parent.awaitable_attrs.components

        # Keep track of existing keys in the DB and keys given in the input list.
        # The ones who are not seen but do exist in our DB should be deleted
        existing_by_key = {component.key: component for component in parent_components}
        seen_keys: set[str] = set()

        for component in input_components:
            if component.key in seen_keys:
                raise Exception(f"Duplicate component key '{component.key}' found. Must be unique within the form.")

            seen_keys.add(component.key)

            if component.key in existing_by_key:
                # Re-add the component to reflect the order from the input list
                parent_components.remove(existing_by_key[component.key])
                parent_components.append(existing_by_key[component.key])

                await self._update_component(existing_by_key[component.key], component)
            else:
                await self._create_component(parent, component)

        for key, component in existing_by_key.items():
            if key not in seen_keys:
                parent_components.remove(component)

        parent_components.reorder()

    async def _create_components(
        self, parent: Form | FormIoPanelComponent, components: Sequence[FormComponentUnion]
    ) -> None:
        for component in components:
            await self._create_component(parent, component)

    async def _create_component(self, parent: Form | FormIoPanelComponent, component: FormComponentUnion) -> None:
        parent_components = await parent.awaitable_attrs.components
        component_values = component.model_dump()

        if isinstance(component, FormPanelComponentInput):
            component_values.pop("components")

            panel_component = FormIoPanelComponent(**component_values)
            parent_components.append(panel_component)

            await self._sync_component_tree(panel_component, component.components)
        else:
            # Remove nested collection data so we don't accidentally assign raw lists to relationship attributes
            value_data = component_values.pop("values", [])
            data = component_values.pop("data", {})

            component_values_with_validate = self._transform_validation_fields(component_values, component.validate_)

            question_component = self._produce_question_component(component_values_with_validate)
            parent_components.append(question_component)

            await self._create_question(component=question_component)

            if isinstance(question_component, (FormIoCheckBoxComponent, FormIoRadioComponent)):
                await self._create_component_values(component=question_component, values=value_data)

            elif isinstance(question_component, FormIoSelectComponent):
                assert data is not None
                select_component_data = FormIoSelectComponentData()
                select_component_data_values = await select_component_data.awaitable_attrs.values

                for value in data.get("values"):
                    component_value = FormIoSelectComponentValue(**value)
                    select_component_data_values.append(component_value)

                select_component_data_values.reorder()
                question_component.data = select_component_data

    async def _update_component(self, existing_component: FormIoComponent, component_input: FormComponentUnion) -> None:
        input_values = component_input.model_dump(exclude_unset=True)

        # Updated component must have the same type as the existing component, otherwise we cannot update in place and need to delete and re-create
        expected_type = input_values.get("type")
        if existing_component.type != expected_type:
            raise HTTPException(
                detail=(
                    f"Component key '{component_input.key}' type mismatch: "
                    f"expected {existing_component.type}, got {expected_type}"
                ),
                status_code=HTTP_400_BAD_REQUEST,
            )

        # If the component is a panel, we need to sync the nested components instead and update the panel attributes.
        if isinstance(component_input, FormPanelComponentInput):
            if not isinstance(existing_component, FormIoPanelComponent):
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Component key '{component_input.key}' type mismatch: expected panel",
                )

            input_values.pop("components")

            for attr, value in input_values.items():
                setattr(existing_component, attr, value)

            await self._sync_component_tree(existing_component, component_input.components)
            return

        # Remove nested collection data so we don't accidentally assign raw lists to relationship attributes
        value_data = input_values.pop("values", None)
        data = input_values.pop("data", None)

        input_with_validate_fields = self._transform_validation_fields(input_values, component_input.validate_)

        # Update attributes within the component model's scope
        for attr, value in input_with_validate_fields.items():
            setattr(existing_component, attr, value)

        # Overwrite nested attributes for label and values components
        if isinstance(existing_component, BaseFormIoValuesComponent) and value_data is not None:
            existing_values = await existing_component.awaitable_attrs.values
            existing_values.clear()
            for value in value_data:
                existing_values.append(FormIoComponentValue(**value))
            existing_values.reorder()

        # Overwrite nested attributes for select component with data.values
        if isinstance(existing_component, FormIoSelectComponent) and data is not None:
            existing_data = await existing_component.awaitable_attrs.data
            if existing_data is None:
                existing_component.data = FormIoSelectComponentData()
                existing_data = existing_component.data

            select_values = await existing_data.awaitable_attrs.values
            select_values.clear()
            for value in data.get("values", []):
                select_values.append(FormIoSelectComponentValue(**value))
            select_values.reorder()

        if isinstance(existing_component, FormIoQuestionComponent):
            question = await existing_component.awaitable_attrs.question
            if question is None:
                # ensure a Question exists for this component
                await self._create_question(existing_component)
            else:
                if question.text != existing_component.label:
                    question.text = existing_component.label
                    await self._question_repository.save(question, commit=False)

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

    def _transform_validation_fields(
        self, values: dict[str, Any], validate: FormComponentInputValidate | None
    ) -> dict[str, Any]:
        """The validation fields can't be dumped by alias directly onto the component model because the validate_ field is not part of the component model
        Therefore we need to transform the validate_ field into the corresponding jsonlogic, required and required_error_message fields expected by the component model
        """

        values.pop("validate_", None)

        if validate is None:
            return values

        if validate.json_ is not None:
            values["jsonlogic"] = validate.json_.model_dump_json(by_alias=True)

        if validate.required is not None:
            values["required"] = validate.required
            values["required_error_message"] = validate.required_error_message

        return values


class FormCreateAction(BaseFormCreateUpdateAction):
    _classification_repository: ClassificationRepository

    def __init__(
        self,
        repository: FormRepository,
        classification_repository: ClassificationRepository,
        question_repository: QuestionRepository,
        form_io_question_component_factory: FormIoQuestionComponentFactory,
    ):
        super().__init__(repository, question_repository, form_io_question_component_factory)
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
        form_io_question_component_factory: FormIoQuestionComponentFactory,
    ):
        super().__init__(repository, question_repository, form_io_question_component_factory)
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

        # Sync components (create/update/delete) based on FormIO keys
        await self._sync_component_tree(obj, form_input.components)

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
    _create_answer: AnswerFactory

    def __init__(
        self,
        repository: AnswerRepository,
        token_verifier: TokenVerifier[Melding],
        question_repository: QuestionRepository,
        component_repository: FormIoQuestionComponentRepository,
        jsonlogic_validator: JSONLogicValidator,
        answer_factory: AnswerFactory,
    ):
        super().__init__(repository)
        self._token_verifier = token_verifier
        self._question_repository = question_repository
        self._component_repository = component_repository
        self._jsonlogic_validate = jsonlogic_validator
        self._create_answer = answer_factory

    async def __call__(self, melding_id: int, token: str, question_id: int, answer_input: AnswerInputUnion) -> Answer:
        """
        Create and store an Answer in the database, subject to several conditions:

        Conditions:
        1. The question must exist
        2. The provided token must be valid
        3. The melding must be classified
        4. The question must belong to an existing and active form.
        5. The form must have a classification
        6. The melding classification must be the same as the form classification
        7. The type of the answer must correspond to the answer type that is expected from the question
        8. If the question has JSONlogic validation, the answer must pass this validation
        """
        # Question must exist
        question = await self._question_repository.retrieve(question_id)
        if question is None:
            raise NotFoundException()

        # Token must be valid
        melding = await self._token_verifier(melding_id, token)

        # Melding must be classified
        if not await melding.awaitable_attrs.classification:
            raise MeldingNotClassifiedException()

        # Question must belong to a form
        form = await question.awaitable_attrs.form
        if form is None:
            raise NotFoundException()

        # Form must have a classification
        form_classification = await form.awaitable_attrs.classification
        if form_classification is None:
            raise NotFoundException()

        # Melding classification must be the same as form classification
        melding_classification = await melding.awaitable_attrs.classification

        if melding_classification != form_classification:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=[{"msg": "Form classification is not the same as melding classification"}],
            )

        # The type of the answer must correspond to the answer type that is expected from the question
        form_component = await self._component_repository.find_component_by_question_id(question.id)
        answer_type_from_question = FormIoComponentToAnswerTypeMap.get(FormIoComponentTypeEnum(form_component.type))

        if answer_type_from_question != answer_input.type:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=[
                    {
                        "msg": f"Given answer type {answer_input.type} does not match expected type {answer_type_from_question}"
                    }
                ],
            )

        # Validate JSONlogic on TextAnswerInput only
        if form_component.jsonlogic is not None and isinstance(answer_input, TextAnswerInput):
            try:
                self._jsonlogic_validate(form_component.jsonlogic, {"text": answer_input.text})
            except JSONLogicValidationException as e:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=[{"msg": e.msg, "input": e.input, "type": "value_error"}],
                ) from e

        answer = self._create_answer(answer_input, melding, question)

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

    async def __call__(self, melding_id: int, token: str, answer_id: int, answer_input: AnswerInputUnion) -> Answer:
        """
        Conditions:
        1. The provided token must be valid
        2. The answer must exist
        3. The answer must belong to the melding identified by melding_id
        4. The type of the answer_input must correspond to the type of the existing answer
        5. If the question has JSONlogic validation, the updated answer must pass this validation
        """

        # Validate token
        melding = await self._token_verifier(melding_id, token)

        # Validate answer exists
        answer = await self._repository.retrieve(answer_id)
        if answer is None:
            raise NotFoundException("Answer not found")

        # Validate answer belongs to melding
        answer_melding = await answer.awaitable_attrs.melding
        if answer_melding != melding:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=[{"msg": "Answer does not belong to melding"}],
            )

        # Validate answer type matches
        if answer.type != answer_input.type:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=[
                    {"msg": f"Given answer type {answer_input.type} does not match existing answer type {answer.type}"}
                ],
            )

        # Validate JSONlogic on TextAnswerInput only
        form_component = await self._component_repository.find_component_by_question_id(answer.question_id)

        if form_component.jsonlogic is not None and isinstance(answer_input, TextAnswerInput):
            try:
                assert answer_input.text is not None
                self._jsonlogic_validate(form_component.jsonlogic, {"text": answer_input.text})
            except JSONLogicValidationException as e:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=[{"msg": e.msg, "input": e.input, "type": "value_error"}],
                ) from e

        # update only the fields that are set in the input
        update_data = answer_input.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(answer, key, value)

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
        self, parent: StaticForm | FormIoPanelComponent, components: Sequence[FormComponentUnion]
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
                        component_values["required_error_message"] = component.validate_.required_error_message

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
