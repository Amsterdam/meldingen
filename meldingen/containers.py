import logging
from functools import lru_cache
from typing import Annotated, AsyncGenerator

from fastapi import Depends

from jwt import PyJWKClient
from meldingen_core.actions.classification import ClassificationCreateAction, ClassificationDeleteAction

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from meldingen.actions import (
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
)
from meldingen.config import Settings
from meldingen.repositories import ClassificationRepository, UserRepository


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_engine(settings: Annotated[Settings, Depends(get_settings)], log_level: int = logging.NOTSET) -> AsyncEngine:
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

    return create_async_engine(str(settings.database_dsn), echo=echo)


async def get_database_session(
    engine: Annotated[AsyncEngine, Depends(get_database_engine)]
) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


def classification_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)]
) -> ClassificationRepository:
    return ClassificationRepository(session)


def classification_create_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationCreateAction:
    return ClassificationCreateAction(repository)


def classification_list_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationListAction:
    return ClassificationListAction(repository)


def classification_retrieve_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationRetrieveAction:
    return ClassificationRetrieveAction(repository)

def classification_update_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationUpdateAction:
    return ClassificationUpdateAction(repository)


def classification_delete_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationDeleteAction:
    return ClassificationDeleteAction(repository)


def jwks_client(settings: Annotated[Settings, Depends(get_settings)]) -> PyJWKClient:
    return PyJWKClient(uri=settings.jwks_url)


def user_repository(session: Annotated[AsyncSession, get_database_session]) -> UserRepository:
    return UserRepository(session)
