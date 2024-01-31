from typing import Generator

import alembic
import pytest
import sqlalchemy
from alembic.config import Config
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy import Engine


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
def alembic_engine() -> Engine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return sqlalchemy.create_engine("postgresql://meldingen:postgres@database:5432/meldingen-test")


@pytest.fixture(scope="session")
def apply_migrations() -> Generator[None, None, None]:
    config = Config("alembic.ini")

    alembic.command.upgrade(config, "head")
    yield
    alembic.command.downgrade(config, "base")
