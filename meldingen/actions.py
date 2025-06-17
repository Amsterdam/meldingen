from typing import Any, Sequence, TypeVar, override

from fastapi import BackgroundTasks, HTTPException
from meldingen_core import SortingDirection
from meldingen_core.actions.attachment import DeleteAttachmentAction as BaseDeleteAttachmentAction
from meldingen_core.actions.attachment import DownloadAttachmentAction as BaseDownloadAttachmentAction
from meldingen_core.actions.attachment import ListAttachmentsAction as BaseListAttachmentsAction
from meldingen_core.actions.attachment import MelderDownloadAttachmentAction as BaseMelderDownloadAttachmentAction
from meldingen_core.actions.attachment import MelderListAttachmentsAction as BaseMelderListAttachmentsAction
from meldingen_core.actions.attachment import UploadAttachmentAction as BaseUploadAttachmentAction
from meldingen_core.actions.base import BaseCRUDAction, BaseDeleteAction
from meldingen_core.actions.base import BaseListAction as BaseCoreListAction
from meldingen_core.actions.base import BaseRetrieveAction
from meldingen_core.actions.classification import ClassificationCreateAction as BaseClassificationCreateAction
from meldingen_core.actions.classification import ClassificationDeleteAction as BaseClassificationDeleteAction
from meldingen_core.actions.classification import ClassificationListAction as BaseClassificationListAction
from meldingen_core.actions.classification import ClassificationRetrieveAction as BaseClassificationRetrieveAction
from meldingen_core.actions.classification import ClassificationUpdateAction as BaseClassificationUpdateAction
from meldingen_core.actions.mail import BasePreviewMailAction
from meldingen_core.actions.melding import MeldingAddContactInfoAction as BaseMeldingAddContactInfoAction
from meldingen_core.actions.melding import MeldingListAction as BaseMeldingListAction
from meldingen_core.actions.melding import MeldingRetrieveAction as BaseMeldingRetrieveAction
from meldingen_core.actions.melding import MeldingSubmitAction as BaseMeldingSubmitAction
from meldingen_core.actions.user import UserCreateAction as BaseUserCreateAction
from meldingen_core.actions.user import UserDeleteAction as BaseUserDeleteAction
from meldingen_core.actions.user import UserListAction as BaseUserListAction
from meldingen_core.actions.user import UserRetrieveAction as BaseUserRetrieveAction
from meldingen_core.actions.user import UserUpdateAction as BaseUserUpdateAction
from meldingen_core.address import BaseAddressEnricher
from meldingen_core.exceptions import NotFoundException
from meldingen_core.statemachine import MeldingStates
from meldingen_core.token import TokenVerifier
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

from meldingen.exceptions import MeldingNotClassifiedException
from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator
from meldingen.location import MeldingLocationIngestor, WKBToPointShapeTransformer
from meldingen.mail import BaseMailPreviewer
from meldingen.models import (
    Answer,
    Attachment,
    BaseFormIoValuesComponent,
    Classification,
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
    User,
)
from meldingen.repositories import (
    AnswerRepository,
    AttributeNotFoundException,
    ClassificationRepository,
    FormIoQuestionComponentRepository,
    FormRepository,
    MeldingRepository,
    QuestionRepository,
    StaticFormRepository,
)
from meldingen.schemas.input import AnswerInput, FormComponent, FormInput, FormPanelComponentInput, StaticFormInput
from meldingen.schemas.types import Address, GeoJson

T = TypeVar("T")


class BaseListAction(BaseCoreListAction[T]):
    async def __call__(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Sequence[T]:
        try:
            return await super().__call__(
                limit=limit, offset=offset, sort_attribute_name=sort_attribute_name, sort_direction=sort_direction
            )
        except AttributeNotFoundException as e:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_ENTITY,
                [{"loc": ("query", "sort"), "msg": e.message, "type": "attribute_not_found"}],
            )


class UserCreateAction(BaseUserCreateAction[User]): ...


class UserListAction(BaseUserListAction[User], BaseListAction[User]): ...


class UserRetrieveAction(BaseUserRetrieveAction[User]): ...


class UserUpdateAction(BaseUserUpdateAction[User]): ...


class UserDeleteAction(BaseUserDeleteAction[User]): ...


class MeldingListAction(BaseMeldingListAction[Melding]):
    @override
    async def __call__(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
        area: str | None = None,
        state: MeldingStates | None = None,
    ) -> Sequence[Melding]:
        try:
            return await super().__call__(
                limit=limit,
                offset=offset,
                sort_attribute_name=sort_attribute_name,
                sort_direction=sort_direction,
                area=area,
                state=state,
            )
        except AttributeNotFoundException as e:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_ENTITY,
                [{"loc": ("query", "sort"), "msg": e.message, "type": "attribute_not_found"}],
            )


class MeldingRetrieveAction(BaseMeldingRetrieveAction[Melding]): ...


class MelderMeldingRetrieveAction:
    _verify_token: TokenVerifier[Melding]

    def __init__(self, token_verifier: TokenVerifier[Melding]):
        self._verify_token = token_verifier

    async def __call__(self, melding_id: int, token: str) -> Melding:
        return await self._verify_token(melding_id, token)


class ClassificationListAction(BaseClassificationListAction[Classification], BaseListAction[Classification]): ...


class ClassificationCreateAction(BaseClassificationCreateAction[Classification]): ...


class ClassificationRetrieveAction(BaseClassificationRetrieveAction[Classification]): ...


class ClassificationUpdateAction(BaseClassificationUpdateAction[Classification]): ...


class ClassificationDeleteAction(BaseClassificationDeleteAction[Classification]): ...


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


class AnswerCreateAction(BaseCRUDAction[Answer]):
    _token_verifier: TokenVerifier[Melding]
    _melding_repository: MeldingRepository
    _question_repository: QuestionRepository
    _component_repository: FormIoQuestionComponentRepository
    _jsonlogic_validate: JSONLogicValidator

    def __init__(
        self,
        repository: AnswerRepository,
        token_verifier: TokenVerifier[Melding],
        melding_repository: MeldingRepository,
        question_repository: QuestionRepository,
        component_repository: FormIoQuestionComponentRepository,
        jsonlogic_validator: JSONLogicValidator,
    ):
        super().__init__(repository)
        self._token_verifier = token_verifier
        self._melding_repository = melding_repository
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
            except JSONLogicValidationException:
                raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid input")

        answer = Answer(**answer_data, melding=melding, question=question)

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


class UploadAttachmentAction(BaseUploadAttachmentAction[Attachment, Melding]): ...


class DownloadAttachmentAction(BaseDownloadAttachmentAction[Attachment]): ...


class MelderDownloadAttachmentAction(BaseMelderDownloadAttachmentAction[Attachment, Melding]): ...


class ListAttachmentsAction(BaseListAttachmentsAction[Attachment]): ...


class MelderListAttachmentsAction(BaseMelderListAttachmentsAction[Attachment, Melding]): ...


class DeleteAttachmentAction(BaseDeleteAttachmentAction[Attachment, Melding]): ...


class AddLocationToMeldingAction:
    _verify_token: TokenVerifier[Melding]
    _ingest_location: MeldingLocationIngestor
    _background_task_manager: BackgroundTasks
    _add_address: BaseAddressEnricher[Melding, Address]
    _wkb_to_point_shape: WKBToPointShapeTransformer

    def __init__(
        self,
        token_verifier: TokenVerifier[Melding],
        location_ingestor: MeldingLocationIngestor,
        background_task_manager: BackgroundTasks,
        address_enricher: BaseAddressEnricher[Melding, Address],
        wkb_to_point_shape_transformer: WKBToPointShapeTransformer,
    ) -> None:
        self._verify_token = token_verifier
        self._ingest_location = location_ingestor
        self._background_task_manager = background_task_manager
        self._add_address = address_enricher
        self._wkb_to_point_shape = wkb_to_point_shape_transformer

    async def __call__(self, melding_id: int, token: str, location: GeoJson) -> Melding:
        melding = await self._verify_token(melding_id, token)
        melding = await self._ingest_location(melding, location)

        assert melding.geo_location is not None
        shape = self._wkb_to_point_shape(melding.geo_location)

        self._background_task_manager.add_task(self._add_address, melding, shape.x, shape.y)

        return melding


class AddContactInfoToMeldingAction(BaseMeldingAddContactInfoAction[Melding]): ...


class MeldingSubmitAction(BaseMeldingSubmitAction[Melding]): ...


class PreviewMailAction(BasePreviewMailAction):
    _get_preview: BaseMailPreviewer

    def __init__(self, previewer: BaseMailPreviewer):
        self._get_preview = previewer

    async def __call__(self, title: str, preview_text: str, body_text: str) -> str:
        return await self._get_preview(title, preview_text, body_text)
