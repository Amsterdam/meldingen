from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Configuration, Singleton, Resource, Factory
from sqlalchemy import Engine
from sqlmodel import create_engine, Session

from meldingen.config import Settings
from meldingen.repositories import MeldingRepository


def get_database_engine(settings: Settings) -> Engine:
    return create_engine(str(settings.get('database_dsn')), echo=True)

def get_database_session(engine: Engine) -> Session:
    with Session(engine) as session:
        yield session


class Container(DeclarativeContainer):
    """Dependency injection container."""

    wiring_config = WiringConfiguration(modules=['meldingen.api.v1.endpoints.melding'])

    settings: Configuration = Configuration(strict=True)
    database_engine: Engine = Singleton(get_database_engine, settings=settings)
    database_session: Session = Resource(get_database_session, engine=database_engine)

    melding_repository: MeldingRepository = Factory(MeldingRepository, session=database_session)
