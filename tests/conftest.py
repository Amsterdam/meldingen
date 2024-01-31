import alembic
import pytest
import sqlalchemy
from pytest_alembic.config import Config
from sqlalchemy import Engine


@pytest.fixture
def alembic_config() -> Config:
    """Override this fixture to configure the exact alembic context setup required."""
    return Config()


@pytest.fixture
def alembic_engine() -> Engine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return sqlalchemy.create_engine("postgresql://meldingen:postgres@database:5432/meldingen-test")


# Apply migrations at beginning and end of testing session
@pytest.fixture(scope="session")
def apply_migrations():
    # warnings.filterwarnings("ignore", category=DeprecationWarning)
    # os.environ["TESTING"] = "1"
    config = Config("alembic.ini")

    alembic.command.upgrade(config, "head")
    yield
    alembic.command.downgrade(config, "base")
