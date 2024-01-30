from typing import Any, Generator

from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Configuration, Factory, Resource, Singleton
from pydantic_core import MultiHostUrl
from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from meldingen.repositories import MeldingRepository


def get_database_engine(dsn: MultiHostUrl) -> Engine:
    return create_engine(str(dsn), echo=True)


def get_database_session(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


class Container(DeclarativeContainer):
    """Dependency injection container."""

    settings: Configuration = Configuration(strict=True)
    database_engine: Singleton[Engine] = Singleton(get_database_engine, dsn=settings.database_dsn)
    database_session: Resource[Session] = Resource(get_database_session, engine=database_engine)

    melding_repository: Factory[MeldingRepository] = Factory(MeldingRepository, session=database_session)
