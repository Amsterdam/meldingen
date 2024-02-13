from typing import AsyncGenerator

from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Configuration, Factory, Resource, Singleton
from jwt import PyJWKClient
from meldingen_core.actions.melding import MeldingCreateAction, MeldingListAction, MeldingRetrieveAction
from meldingen_core.actions.user import UserCreateAction, UserListAction, UserRetrieveAction
from pydantic_core import MultiHostUrl
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from meldingen.repositories import MeldingRepository, UserRepository


def get_database_engine(dsn: MultiHostUrl) -> AsyncEngine:
    return create_async_engine(str(dsn), echo=True)


async def get_database_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session


class Container(DeclarativeContainer):
    """Dependency injection container."""

    wiring_config: WiringConfiguration = WiringConfiguration(
        modules=["meldingen.api.v1.endpoints.melding", "meldingen.api.v1.endpoints.user", "meldingen.authentication"]
    )

    settings: Configuration = Configuration(strict=True)
    database_engine: Singleton[AsyncEngine] = Singleton(get_database_engine, dsn=settings.database_dsn)
    database_session: Resource[AsyncSession] = Resource(get_database_session, engine=database_engine)

    # repositories
    melding_repository: Factory[MeldingRepository] = Factory(MeldingRepository, session=database_session)
    user_repository: Factory[UserRepository] = Factory(UserRepository, session=database_session)

    # actions
    melding_create_action: Factory[MeldingCreateAction] = Factory(MeldingCreateAction, repository=melding_repository)
    melding_list_action: Factory[MeldingListAction] = Factory(MeldingListAction, repository=melding_repository)
    melding_retrieve_action: Factory[MeldingRetrieveAction] = Factory(
        MeldingRetrieveAction, repository=melding_repository
    )
    user_create_action: Factory[UserCreateAction] = Factory(UserCreateAction, repository=user_repository)
    user_list_action: Factory[UserListAction] = Factory(UserListAction, repository=user_repository)
    user_retrieve_action: Factory[UserRetrieveAction] = Factory(UserRetrieveAction, repository=user_repository)

    # authentication
    jwks_client: Singleton[PyJWKClient] = Singleton(PyJWKClient, uri=settings.jwks_url)
