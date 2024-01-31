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


@pytest.fixture
def apply_migrations() -> None:
    config = Config("alembic.ini")

    alembic.command.downgrade(config, "base")
    alembic.command.upgrade(config, "head")
