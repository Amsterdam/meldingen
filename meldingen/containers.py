import logging
from typing import Any, AsyncIterator, Iterator, TypeVar

from jwt import PyJWKClient, PyJWT
from meldingen_core.actions.classification import ClassificationCreateAction, ClassificationDeleteAction
from pydantic_core import MultiHostUrl
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from that_depends.container import BaseContainer
from that_depends.providers import AsyncResource, Factory, Resource, Singleton

from meldingen.actions import ClassificationListAction, ClassificationRetrieveAction, ClassificationUpdateAction
from meldingen.config import settings
from meldingen.repositories import ClassificationRepository


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


async def get_database_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


async def _classification_repository(session: AsyncSession) -> AsyncIterator[ClassificationRepository]:
    yield ClassificationRepository(session)


R = TypeVar("R")


async def _async_resource_factory(klass: R, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> AsyncIterator[R]:
    yield klass(*args, **kwargs)


class Container(BaseContainer):
    """Dependency injection container."""

    # Database
    database_engine: Singleton[AsyncEngine] = Singleton(
        get_database_engine, dsn=settings.database_dsn, log_level=settings.log_level
    )
    database_session: AsyncResource[AsyncSession] = AsyncResource(get_database_session, engine=database_engine.cast)

    # Repositories
    classification_repository: AsyncResource[ClassificationRepository] = AsyncResource(
        _classification_repository, session=database_session.cast
    )

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
