import logging
from functools import lru_cache
from typing import Annotated, AsyncIterator

from fastapi import Depends
from jwt import PyJWKClient, PyJWT
from meldingen_core.actions.melding import (
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingCreateAction,
    MeldingProcessAction,
    MeldingUpdateAction,
)
from meldingen_core.classification import Classifier
from meldingen_core.statemachine import MeldingTransitions
from meldingen_core.token import BaseTokenGenerator, TokenVerifier
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from meldingen.actions import (
    AnswerCreateAction,
    ClassificationCreateAction,
    ClassificationDeleteAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
    MeldingListAction,
    MeldingRetrieveAction,
)
from meldingen.classification import DummyClassifierAdapter
from meldingen.config import settings
from meldingen.database import DatabaseSessionManager
from meldingen.models import Melding
from meldingen.repositories import (
    AnswerRepository,
    ClassificationRepository,
    MeldingRepository,
    QuestionRepository,
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


def classifier(repository: Annotated[ClassificationRepository, Depends(classification_repository)]) -> Classifier:
    return Classifier(DummyClassifierAdapter(), repository)


def token_generator() -> BaseTokenGenerator:
    return UrlSafeTokenGenerator()


def token_verifier() -> TokenVerifier[Melding]:
    return TokenVerifier()


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


def melding_answer_create_action(
    answer_repository: Annotated[AnswerRepository, Depends(answer_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    melding_repository: Annotated[MeldingRepository, Depends(melding_repository)],
    question_repository: Annotated[QuestionRepository, Depends(question_repository)],
) -> AnswerCreateAction:
    return AnswerCreateAction(answer_repository, token_verifier, melding_repository, question_repository)


def jwks_client() -> PyJWKClient:
    return PyJWKClient(settings.jwks_url)


def py_jwt() -> PyJWT:
    return PyJWT()
