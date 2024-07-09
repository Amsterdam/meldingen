import logging
from typing import AsyncGenerator

from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Configuration, Factory, Resource, Singleton
from jwt import PyJWKClient, PyJWT
from meldingen_core.actions.classification import ClassificationCreateAction, ClassificationDeleteAction
from meldingen_core.actions.melding import (
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingCreateAction,
    MeldingProcessAction,
    MeldingUpdateAction,
)
from meldingen_core.actions.user import UserCreateAction, UserDeleteAction
from meldingen_core.classification import Classifier
from meldingen_core.statemachine import MeldingTransitions
from meldingen_core.token import TokenVerifier
from mp_fsm.statemachine import BaseGuard, BaseTransition
from plugfs.filesystem import Filesystem
from plugfs.local import LocalAdapter
from pydantic_core import MultiHostUrl
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from meldingen.actions import (
    AnswerCreateAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
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
    UserListAction,
    UserRetrieveAction,
    UserUpdateAction,
)
from meldingen.classification import DummyClassifierAdapter
from meldingen.factories import AttachmentFactory
from meldingen.models import Melding
from meldingen.repositories import (
    AnswerRepository,
    AttachmentRepository,
    ClassificationRepository,
    FormRepository,
    GroupRepository,
    MeldingRepository,
    QuestionRepository,
    StaticFormRepository,
    UserRepository,
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


def get_database_engine(dsn: MultiHostUrl, log_level: int = logging.NOTSET) -> AsyncEngine:
    """Returns an async database engine.

    echo can be configured via the environment variable for log_level.

    "This has the effect of setting the Python logging level for the namespace
    of this element’s class and object reference. A value of boolean True
    indicates that the loglevel logging.INFO will be set for the logger,
    whereas the string value debug will set the loglevel to logging.DEBUG."

    More info on: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncEngine.echo
    """
    echo: bool | str = False
    match log_level:  # pragma: no cover
        case logging.INFO:
            echo = True
        case logging.DEBUG:
            echo = "debug"

    return create_async_engine(str(dsn), echo=echo)


async def get_database_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


def get_transitions(
    classify: Classify, answer_questions: AnswerQuestions, process: Process, complete: Complete
) -> dict[str, BaseTransition[Melding]]:
    return {
        MeldingTransitions.CLASSIFY: classify,
        MeldingTransitions.ANSWER_QUESTIONS: answer_questions,
        MeldingTransitions.PROCESS: process,
        MeldingTransitions.COMPLETE: complete,
    }


def get_classify_guards(has_classification: HasClassification) -> list[BaseGuard[Melding]]:
    return [has_classification]


class Container(DeclarativeContainer):
    """Dependency injection container."""

    wiring_config: WiringConfiguration = WiringConfiguration(
        modules=[
            "meldingen.api.v1.endpoints.melding",
            "meldingen.api.v1.endpoints.user",
            "meldingen.authentication",
            "meldingen.api.v1.endpoints.classification",
            "meldingen.api.v1.endpoints.form",
            "meldingen.api.v1.endpoints.static_form",
        ]
    )

    settings: Configuration = Configuration(strict=True)
    database_engine: Singleton[AsyncEngine] = Singleton(
        get_database_engine, dsn=settings.database_dsn, log_level=settings.log_level
    )
    database_session: Resource[AsyncSession] = Resource(get_database_session, engine=database_engine)

    # repositories
    melding_repository: Factory[MeldingRepository] = Factory(MeldingRepository, session=database_session)
    user_repository: Factory[UserRepository] = Factory(UserRepository, session=database_session)
    group_repository: Factory[GroupRepository] = Factory(GroupRepository, session=database_session)
    classification_repository: Factory[ClassificationRepository] = Factory(
        ClassificationRepository, session=database_session
    )
    form_repository: Factory[FormRepository] = Factory(FormRepository, session=database_session)
    static_form_repository: Factory[StaticFormRepository] = Factory(StaticFormRepository, session=database_session)
    question_repository: Factory[QuestionRepository] = Factory(QuestionRepository, session=database_session)
    answer_repository: Factory[AnswerRepository] = Factory(AnswerRepository, session=database_session)
    attachment_repository: Factory[AttachmentRepository] = Factory(AttachmentRepository, session=database_session)

    # state machine
    melding_has_classification_guard: Singleton[HasClassification] = Singleton(HasClassification)
    melding_classify_transition_guards: Singleton[list[BaseGuard[Melding]]] = Singleton(
        get_classify_guards, has_classification=melding_has_classification_guard
    )
    melding_classify_transition: Singleton[Classify] = Singleton(Classify, guards=melding_classify_transition_guards)
    answer_questions_transition: Singleton[AnswerQuestions] = Singleton(AnswerQuestions)
    melding_process_transition: Singleton[Process] = Singleton(Process)
    melding_complete_transition: Singleton[Complete] = Singleton(Complete)
    melding_transitions: Singleton[dict[str, BaseTransition[Melding]]] = Singleton(
        get_transitions,
        classify=melding_classify_transition,
        answer_questions=answer_questions_transition,
        process=melding_process_transition,
        complete=melding_complete_transition,
    )
    mp_fsm_melding_state_machine: Singleton[MpFsmMeldingStateMachine] = Singleton(
        MpFsmMeldingStateMachine, transitions=melding_transitions
    )
    melding_state_machine: Singleton[MeldingStateMachine] = Singleton(
        MeldingStateMachine, state_machine=mp_fsm_melding_state_machine
    )

    # classifier
    dummy_classifier_adaper: Singleton[DummyClassifierAdapter] = Singleton(DummyClassifierAdapter)
    classifier: Singleton[Classifier] = Singleton(
        Classifier, adapter=dummy_classifier_adaper, repository=classification_repository
    )

    # token
    token_generator: Singleton[UrlSafeTokenGenerator] = Singleton(UrlSafeTokenGenerator)
    token_verifier: Singleton[TokenVerifier[Melding]] = Singleton(TokenVerifier)

    # filesystem
    filesystem_adapter: Factory[LocalAdapter] = Factory(LocalAdapter)
    filesystem: Factory[Filesystem] = Factory(Filesystem, adapter=filesystem_adapter)

    # Factories
    attachment_factory: Factory[AttachmentFactory] = Factory(AttachmentFactory)

    # Meldingen actions
    melding_create_action: Factory[MeldingCreateAction[Melding, Melding]] = Factory(
        MeldingCreateAction,
        repository=melding_repository,
        classifier=classifier,
        state_machine=melding_state_machine,
        token_generator=token_generator,
        token_duration=settings.token_duration,
    )
    melding_list_action: Factory[MeldingListAction] = Factory(MeldingListAction, repository=melding_repository)
    melding_retrieve_action: Factory[MeldingRetrieveAction] = Factory(
        MeldingRetrieveAction, repository=melding_repository
    )
    melding_update_action: Factory[MeldingUpdateAction[Melding, Melding]] = Factory(
        MeldingUpdateAction,
        repository=melding_repository,
        token_verifier=token_verifier,
        classifier=classifier,
        state_machine=melding_state_machine,
    )
    melding_answer_questions_action: Factory[MeldingAnswerQuestionsAction[Melding, Melding]] = Factory(
        MeldingAnswerQuestionsAction,
        state_machine=melding_state_machine,
        repository=melding_repository,
        token_verifier=token_verifier,
    )
    melding_process_action: Factory[MeldingProcessAction[Melding, Melding]] = Factory(
        MeldingProcessAction, state_machine=melding_state_machine, repository=melding_repository
    )
    melding_complete_action: Factory[MeldingCompleteAction[Melding, Melding]] = Factory(
        MeldingCompleteAction, state_machine=melding_state_machine, repository=melding_repository
    )

    # User actions
    user_create_action: Factory[UserCreateAction] = Factory(UserCreateAction, repository=user_repository)
    user_list_action: Factory[UserListAction] = Factory(UserListAction, repository=user_repository)
    user_retrieve_action: Factory[UserRetrieveAction] = Factory(UserRetrieveAction, repository=user_repository)
    user_delete_action: Factory[UserDeleteAction] = Factory(UserDeleteAction, repository=user_repository)
    user_update_action: Factory[UserUpdateAction] = Factory(UserUpdateAction, repository=user_repository)

    # Classification actions
    classification_create_action: Factory[ClassificationCreateAction] = Factory(
        ClassificationCreateAction, repository=classification_repository
    )
    classification_list_action: Factory[ClassificationListAction] = Factory(
        ClassificationListAction, repository=classification_repository
    )
    classification_retrieve_action: Factory[ClassificationRetrieveAction] = Factory(
        ClassificationRetrieveAction, repository=classification_repository
    )
    classification_update_action: Factory[ClassificationUpdateAction] = Factory(
        ClassificationUpdateAction, repository=classification_repository
    )
    classification_delete_action: Factory[ClassificationDeleteAction] = Factory(
        ClassificationDeleteAction, repository=classification_repository
    )

    # Form actions
    form_list_action: Factory[FormListAction] = Factory(FormListAction, repository=form_repository)
    form_retrieve_action: Factory[FormRetrieveAction] = Factory(FormRetrieveAction, repository=form_repository)
    form_create_action: Factory[FormCreateAction] = Factory(
        FormCreateAction,
        repository=form_repository,
        classification_repository=classification_repository,
        question_repository=question_repository,
    )
    form_update_action: Factory[FormUpdateAction] = Factory(
        FormUpdateAction,
        repository=form_repository,
        classification_repository=classification_repository,
        question_repository=question_repository,
    )
    form_delete_action: Factory[FormDeleteAction] = Factory(FormDeleteAction, repository=form_repository)
    form_classification_action: Factory[FormRetrieveByClassificationAction] = Factory(
        FormRetrieveByClassificationAction, repository=form_repository
    )

    # StaticForm actions
    static_form_retrieve_by_type_action: Factory[StaticFormRetrieveByTypeAction] = Factory(
        StaticFormRetrieveByTypeAction, repository=static_form_repository
    )
    static_form_update_action: Factory[StaticFormUpdateAction] = Factory(
        StaticFormUpdateAction, repository=static_form_repository
    )

    # Answer actions
    answer_create_action: Factory[AnswerCreateAction] = Factory(
        AnswerCreateAction,
        repository=answer_repository,
        token_verifier=token_verifier,
        melding_repository=melding_repository,
        question_repository=question_repository,
    )

    # Attachment actions
    upload_attachment_action: Factory[UploadAttachmentAction] = Factory(
        UploadAttachmentAction,
        attachment_factory=attachment_factory,
        attachment_repository=attachment_repository,
        melding_repository=melding_repository,
        filesystem=filesystem,
        token_verifier=token_verifier,
        base_directory="/tmp",
    )

    # authentication
    py_jwt: Singleton[PyJWT] = Singleton(PyJWT)
    jwks_client: Singleton[PyJWKClient] = Singleton(PyJWKClient, uri=settings.jwks_url)
