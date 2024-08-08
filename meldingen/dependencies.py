import logging
from functools import lru_cache
from typing import Annotated, AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from meldingen.actions import (
    ClassificationDeleteAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
)
from meldingen.config import settings
from meldingen.database import DatabaseSessionManager
from meldingen.repositories import ClassificationRepository


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
