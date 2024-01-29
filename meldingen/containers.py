from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Configuration


class Container(DeclarativeContainer):
    """Dependency injection container."""
    settings: Configuration = Configuration()
