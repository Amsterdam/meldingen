import logging
from functools import lru_cache
from typing import Annotated, AsyncIterator

from fastapi import Depends
from jwt import PyJWKClient, PyJWT
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from meldingen.actions import (
    ClassificationCreateAction,
    ClassificationDeleteAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
)
from meldingen.config import settings
from meldingen.database import DatabaseSessionManager
from meldingen.repositories import ClassificationRepository, MeldingRepository, UserRepository


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


def jwks_client() -> PyJWKClient:
    return PyJWKClient(settings.jwks_url)


def py_jwt() -> PyJWT:
    return PyJWT()
