import logging
from functools import lru_cache
from typing import Annotated, AsyncIterator

from fastapi import Depends
from jwt import PyJWKClient, PyJWT
from meldingen_core.actions.melding import (
    MeldingAddAttachmentsAction,
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingCreateAction,
    MeldingProcessAction,
    MeldingUpdateAction,
)
from meldingen_core.classification import Classifier
from meldingen_core.statemachine import MeldingTransitions
from meldingen_core.token import BaseTokenGenerator, TokenVerifier
from plugfs.filesystem import Adapter, Filesystem
from plugfs.local import LocalAdapter
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from meldingen.actions import (
    AnswerCreateAction,
    ClassificationCreateAction,
    ClassificationDeleteAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
    DownloadAttachmentAction,
    FormCreateAction,
    FormDeleteAction,
    FormListAction,
    FormRetrieveAction,
    FormRetrieveByClassificationAction,
    FormUpdateAction,
    MeldingListAction,
    MeldingRetrieveAction,
    StaticFormRetrieveByTypeAction,
    StaticFormUpdateAction,
    UploadAttachmentAction,
    UserCreateAction,
    UserDeleteAction,
    UserListAction,
    UserRetrieveAction,
    UserUpdateAction,
)
from meldingen.classification import DummyClassifierAdapter
from meldingen.config import settings
from meldingen.database import DatabaseSessionManager
from meldingen.factories import AttachmentFactory
from meldingen.jsonlogic import JSONLogicValidator
from meldingen.models import Melding
from meldingen.repositories import (
    AnswerRepository,
    AttachmentRepository,
    ClassificationRepository,
    FormIoQuestionComponentRepository,
    FormRepository,
    MeldingRepository,
    QuestionRepository,
    StaticFormRepository,
    UserRepository,
)
from meldingen.schema_factories import (
    FormCheckboxComponentOutputFactory,
    FormComponentOutputFactory,
    FormComponentValueOutputFactory,
    FormOutputFactory,
    FormRadioComponentOutputFactory,
    FormSelectComponentDataOutputFactory,
    FormSelectComponentOutputFactory,
    FormTextAreaComponentOutputFactory,
    FormTextFieldInputComponentOutputFactory,
    StaticFormCheckboxComponentOutputFactory,
    StaticFormComponentOutputFactory,
    StaticFormOutputFactory,
    StaticFormRadioComponentOutputFactory,
    StaticFormSelectComponentOutputFactory,
    StaticFormTextAreaComponentOutputFactory,
    StaticFormTextFieldInputComponentOutputFactory,
    ValidateAdder,
)
from meldingen.statemachine import (
    AnswerQuestions,
    Classify,
    Complete,
    HasClassification,
    MeldingStateMachine,
    MpFsmMeldingStateMachine,
    Process,
)
from meldingen.token import UrlSafeTokenGenerator
from meldingen.validators import MediaTypeIntegrityValidator, MediaTypeValidator


@lru_cache
def database_engine() -> AsyncEngine:
    echo: bool | str = False
    match settings.log_level:  # pragma: no cover
        case logging.INFO:
            echo = True
        case logging.DEBUG:
            echo = "debug"

    return create_async_engine(str(settings.database_dsn), echo=echo)


def database_session_manager(engine: Annotated[AsyncEngine, Depends(database_engine)]) -> DatabaseSessionManager:
    return DatabaseSessionManager(engine)


async def database_session(
    sessionmanager: Annotated[DatabaseSessionManager, Depends(database_session_manager)]
) -> AsyncIterator[AsyncSession]:
    async with sessionmanager.session() as session:
        yield session


def classification_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> ClassificationRepository:
    return ClassificationRepository(session)


def classification_create_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationCreateAction:
    return ClassificationCreateAction(repository)


def classification_retrieve_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationRetrieveAction:
    return ClassificationRetrieveAction(repository)


def classification_list_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationListAction:
    return ClassificationListAction(repository)


def classification_delete_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationDeleteAction:
    return ClassificationDeleteAction(repository)


def classification_update_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationUpdateAction:
    return ClassificationUpdateAction(repository)


def user_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> UserRepository:
    return UserRepository(session)


def melding_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> MeldingRepository:
    return MeldingRepository(session)


def answer_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> AnswerRepository:
    return AnswerRepository(session)


def question_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> QuestionRepository:
    return QuestionRepository(session)


def attachment_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> AttachmentRepository:
    return AttachmentRepository(session)


def classifier(repository: Annotated[ClassificationRepository, Depends(classification_repository)]) -> Classifier:
    return Classifier(DummyClassifierAdapter(), repository)


def token_generator() -> BaseTokenGenerator:
    return UrlSafeTokenGenerator()


def token_verifier() -> TokenVerifier[Melding]:
    return TokenVerifier()


def attachment_factory() -> AttachmentFactory:
    return AttachmentFactory()


def melding_state_machine() -> MeldingStateMachine:
    return MeldingStateMachine(
        MpFsmMeldingStateMachine(
            {
                MeldingTransitions.CLASSIFY: Classify([HasClassification()]),
                MeldingTransitions.ANSWER_QUESTIONS: AnswerQuestions(),
                MeldingTransitions.PROCESS: Process(),
                MeldingTransitions.COMPLETE: Complete(),
            }
        )
    )


def melding_create_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    classifier: Annotated[Classifier, Depends(classifier)],
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    token_generator: Annotated[BaseTokenGenerator, Depends(token_generator)],
) -> MeldingCreateAction[Melding, Melding]:
    return MeldingCreateAction(repository, classifier, state_machine, token_generator, settings.token_duration)


def melding_retrieve_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)]
) -> MeldingRetrieveAction:
    return MeldingRetrieveAction(repository)


def melding_list_action(repository: Annotated[MeldingRepository, Depends(melding_repository)]) -> MeldingListAction:
    return MeldingListAction(repository)


def melding_update_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    classifier: Annotated[Classifier, Depends(classifier)],
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
) -> MeldingUpdateAction[Melding, Melding]:
    return MeldingUpdateAction(repository, token_verifier, classifier, state_machine)


def melding_answer_questions_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> MeldingAnswerQuestionsAction[Melding, Melding]:
    return MeldingAnswerQuestionsAction(state_machine, repository, token_verifier)


def melding_add_attachments_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> MeldingAddAttachmentsAction[Melding, Melding]:
    return MeldingAddAttachmentsAction(state_machine, repository, token_verifier)


def melding_process_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> MeldingProcessAction[Melding, Melding]:
    return MeldingProcessAction(state_machine, repository)


def melding_complete_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> MeldingCompleteAction[Melding, Melding]:
    return MeldingCompleteAction(state_machine, repository)


def jsonlogic_validator() -> JSONLogicValidator:
    return JSONLogicValidator()


def form_io_question_component_repository(
    session: Annotated[AsyncSession, Depends(database_session)]
) -> FormIoQuestionComponentRepository:
    return FormIoQuestionComponentRepository(session)


def melding_answer_create_action(
    answer_repository: Annotated[AnswerRepository, Depends(answer_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    melding_repository: Annotated[MeldingRepository, Depends(melding_repository)],
    question_repository: Annotated[QuestionRepository, Depends(question_repository)],
    component_repository: Annotated[FormIoQuestionComponentRepository, Depends(form_io_question_component_repository)],
    jsonlogic_validator: Annotated[JSONLogicValidator, Depends(jsonlogic_validator)],
) -> AnswerCreateAction:
    return AnswerCreateAction(
        answer_repository,
        token_verifier,
        melding_repository,
        question_repository,
        component_repository,
        jsonlogic_validator,
    )


def filesystem_adapter() -> Adapter:
    return LocalAdapter()


def filesystem(adapter: Annotated[Adapter, Depends(filesystem_adapter)]) -> Filesystem:
    return Filesystem(adapter)


def media_type_validator() -> MediaTypeValidator:
    return MediaTypeValidator(settings.attachment_allow_media_types)


def media_type_integrity_validator() -> MediaTypeIntegrityValidator:
    return MediaTypeIntegrityValidator()


def melding_upload_attachment_action(
    factory: Annotated[AttachmentFactory, Depends(attachment_factory)],
    repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    melding_repository: Annotated[MeldingRepository, Depends(melding_repository)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    media_type_validator: Annotated[MediaTypeValidator, Depends(media_type_validator)],
    media_type_integrity_validator: Annotated[MediaTypeIntegrityValidator, Depends(media_type_integrity_validator)],
) -> UploadAttachmentAction:
    return UploadAttachmentAction(
        factory,
        repository,
        melding_repository,
        filesystem,
        token_verifier,
        media_type_validator,
        media_type_integrity_validator,
        str(settings.attachment_storage_base_directory),
    )


def melding_download_attachment_action(
    melding_repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
) -> DownloadAttachmentAction:
    return DownloadAttachmentAction(melding_repository, token_verifier, attachment_repository, filesystem)


def form_component_value_output_factory() -> FormComponentValueOutputFactory:
    return FormComponentValueOutputFactory()


def form_select_component_data_output_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)]
) -> FormSelectComponentDataOutputFactory:
    return FormSelectComponentDataOutputFactory(factory)


def static_form_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> StaticFormRepository:
    return StaticFormRepository(session)


def static_form_retrieve_by_type_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)]
) -> StaticFormRetrieveByTypeAction:
    return StaticFormRetrieveByTypeAction(repository)


def static_form_update_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)]
) -> StaticFormUpdateAction:
    return StaticFormUpdateAction(repository)


def validate_adder() -> ValidateAdder:
    return ValidateAdder()


def static_form_text_area_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> StaticFormTextAreaComponentOutputFactory:
    return StaticFormTextAreaComponentOutputFactory(_validate_adder)


def static_form_text_field_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> StaticFormTextFieldInputComponentOutputFactory:
    return StaticFormTextFieldInputComponentOutputFactory(_validate_adder)


def static_form_checkbox_output_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> StaticFormCheckboxComponentOutputFactory:
    return StaticFormCheckboxComponentOutputFactory(factory, _validate_adder)


def static_form_radio_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> StaticFormRadioComponentOutputFactory:
    return StaticFormRadioComponentOutputFactory(factory, _validate_adder)


def static_form_select_factory(
    factory: Annotated[FormSelectComponentDataOutputFactory, Depends(form_select_component_data_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> StaticFormSelectComponentOutputFactory:
    return StaticFormSelectComponentOutputFactory(factory, _validate_adder)


def static_form_component_output_factory(
    text_area_factory: Annotated[
        StaticFormTextAreaComponentOutputFactory, Depends(static_form_text_area_output_factory)
    ],
    text_field_factory: Annotated[
        StaticFormTextFieldInputComponentOutputFactory, Depends(static_form_text_field_output_factory)
    ],
    checkbox_factory: Annotated[StaticFormCheckboxComponentOutputFactory, Depends(static_form_checkbox_output_factory)],
    radio_factory: Annotated[StaticFormRadioComponentOutputFactory, Depends(static_form_radio_factory)],
    select_factory: Annotated[StaticFormSelectComponentOutputFactory, Depends(static_form_select_factory)],
) -> StaticFormComponentOutputFactory:
    return StaticFormComponentOutputFactory(
        text_area_factory,
        text_field_factory,
        checkbox_factory,
        radio_factory,
        select_factory,
    )


def static_form_output_factory(
    factory: Annotated[StaticFormComponentOutputFactory, Depends(static_form_component_output_factory)]
) -> StaticFormOutputFactory:
    return StaticFormOutputFactory(factory)


def form_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> FormRepository:
    return FormRepository(session)


def form_text_area_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> FormTextAreaComponentOutputFactory:
    return FormTextAreaComponentOutputFactory(_validate_adder)


def form_text_field_input_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> FormTextFieldInputComponentOutputFactory:
    return FormTextFieldInputComponentOutputFactory(_validate_adder)


def form_checkbox_output_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> FormCheckboxComponentOutputFactory:
    return FormCheckboxComponentOutputFactory(factory, _validate_adder)


def form_radio_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> FormRadioComponentOutputFactory:
    return FormRadioComponentOutputFactory(factory, _validate_adder)


def form_select_factory(
    factory: Annotated[FormSelectComponentDataOutputFactory, Depends(form_select_component_data_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> FormSelectComponentOutputFactory:
    return FormSelectComponentOutputFactory(factory, _validate_adder)


def form_component_output_factory(
    text_area_factory: Annotated[FormTextAreaComponentOutputFactory, Depends(form_text_area_output_factory)],
    text_field_factory: Annotated[FormTextFieldInputComponentOutputFactory, Depends(form_text_field_input_factory)],
    checkbox_factory: Annotated[FormCheckboxComponentOutputFactory, Depends(form_checkbox_output_factory)],
    radio_factory: Annotated[FormRadioComponentOutputFactory, Depends(form_radio_factory)],
    select_factory: Annotated[FormSelectComponentOutputFactory, Depends(form_select_factory)],
) -> FormComponentOutputFactory:
    return FormComponentOutputFactory(
        text_area_factory,
        text_field_factory,
        checkbox_factory,
        radio_factory,
        select_factory,
    )


def form_output_factory(
    factory: Annotated[FormComponentOutputFactory, Depends(form_component_output_factory)]
) -> FormOutputFactory:
    return FormOutputFactory(factory)


def form_create_action(
    repository: Annotated[FormRepository, Depends(form_repository)],
    classification_repository: Annotated[ClassificationRepository, Depends(classification_repository)],
    question_repository: Annotated[QuestionRepository, Depends(question_repository)],
) -> FormCreateAction:
    return FormCreateAction(repository, classification_repository, question_repository)


def form_list_action(repository: Annotated[FormRepository, Depends(form_repository)]) -> FormListAction:
    return FormListAction(repository)


def form_retrieve_action(repository: Annotated[FormRepository, Depends(form_repository)]) -> FormRetrieveAction:
    return FormRetrieveAction(repository)


def form_retrieve_by_classification_action(
    repository: Annotated[FormRepository, Depends(form_repository)]
) -> FormRetrieveByClassificationAction:
    return FormRetrieveByClassificationAction(repository)


def form_update_action(
    repository: Annotated[FormRepository, Depends(form_repository)],
    classification_repository: Annotated[ClassificationRepository, Depends(classification_repository)],
    question_repository: Annotated[QuestionRepository, Depends(question_repository)],
) -> FormUpdateAction:
    return FormUpdateAction(repository, classification_repository, question_repository)


def form_delete_action(repository: Annotated[FormRepository, Depends(form_repository)]) -> FormDeleteAction:
    return FormDeleteAction(repository)


def jwks_client() -> PyJWKClient:
    return PyJWKClient(settings.jwks_url)


def py_jwt() -> PyJWT:
    return PyJWT()


def user_create_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserCreateAction:
    return UserCreateAction(repository)


def user_list_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserListAction:
    return UserListAction(repository)


def user_retrieve_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserRetrieveAction:
    return UserRetrieveAction(repository)


def user_update_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserUpdateAction:
    return UserUpdateAction(repository)


def user_delete_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserDeleteAction:
    return UserDeleteAction(repository)
