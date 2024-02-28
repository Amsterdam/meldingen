from typing import AsyncGenerator

from casbin import AsyncEnforcer
from casbin_async_sqlalchemy_adapter import Adapter
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Configuration, Factory, Resource, Singleton
from jwt import PyJWKClient
from meldingen_core.actions.classification import (
    ClassificationCreateAction,
    ClassificationDeleteAction,
    ClassificationUpdateAction,
)
from meldingen_core.actions.melding import MeldingCreateAction
from meldingen_core.actions.user import UserCreateAction, UserDeleteAction, UserUpdateAction
from pydantic_core import MultiHostUrl
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from meldingen.actions import (
    ClassificationListAction,
    ClassificationRetrieveAction,
    MeldingListAction,
    MeldingRetrieveAction,
    UserListAction,
    UserRetrieveAction,
)
from meldingen.authorization import Authorizer
from meldingen.repositories import ClassificationRepository, GroupRepository, MeldingRepository, UserRepository


def get_database_engine(dsn: MultiHostUrl) -> AsyncEngine:
    return create_async_engine(str(dsn), echo=True)


async def get_database_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


async def get_casbin_enforcer(model_path: str, adapter: Adapter, enable_log: bool = True) -> AsyncEnforcer:
    casbin_enforcer = AsyncEnforcer(model_path, adapter, enable_log)
    await casbin_enforcer.load_policy()

    return casbin_enforcer


class Container(DeclarativeContainer):
    """Dependency injection container."""

    wiring_config: WiringConfiguration = WiringConfiguration(
        modules=[
            "meldingen.api.v1.endpoints.melding",
            "meldingen.api.v1.endpoints.user",
            "meldingen.authentication",
            "meldingen.api.v1.endpoints.classification",
        ]
    )

    settings: Configuration = Configuration(strict=True)
    database_engine: Singleton[AsyncEngine] = Singleton(get_database_engine, dsn=settings.database_dsn)
    database_session: Resource[AsyncSession] = Resource(get_database_session, engine=database_engine)

    # repositories
    melding_repository: Factory[MeldingRepository] = Factory(MeldingRepository, session=database_session)
    user_repository: Factory[UserRepository] = Factory(UserRepository, session=database_session)
    group_repository: Factory[GroupRepository] = Factory(GroupRepository, session=database_session)
    classification_repository: Factory[ClassificationRepository] = Factory(
        ClassificationRepository, session=database_session
    )

    # actions
    melding_create_action: Factory[MeldingCreateAction] = Factory(MeldingCreateAction, repository=melding_repository)
    melding_list_action: Factory[MeldingListAction] = Factory(MeldingListAction, repository=melding_repository)
    melding_retrieve_action: Factory[MeldingRetrieveAction] = Factory(
        MeldingRetrieveAction, repository=melding_repository
    )
    user_create_action: Factory[UserCreateAction] = Factory(UserCreateAction, repository=user_repository)
    user_list_action: Factory[UserListAction] = Factory(UserListAction, repository=user_repository)
    user_retrieve_action: Factory[UserRetrieveAction] = Factory(UserRetrieveAction, repository=user_repository)
    user_delete_action: Factory[UserDeleteAction] = Factory(UserDeleteAction, repository=user_repository)
    user_update_action: Factory[UserUpdateAction] = Factory(UserUpdateAction, repository=user_repository)
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

    # authentication
    jwks_client: Singleton[PyJWKClient] = Singleton(PyJWKClient, uri=settings.jwks_url)

    # authorization
    casbin_adapter: Singleton[Adapter] = Singleton(Adapter, engine=database_engine)
    casbin_enforcer: Singleton[AsyncEnforcer] = Singleton(
        get_casbin_enforcer, model_path=settings.casbin_model_path, adapter=casbin_adapter, enable_log=True
    )
    authorizer: Singleton[Authorizer] = Singleton(Authorizer, enforcer=casbin_enforcer)
