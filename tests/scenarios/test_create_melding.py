from pytest_bdd import scenario

from tests.scenarios.context.classification import *  # noqa
from tests.scenarios.context.melding import *  # noqa


@scenario("create_melding.feature", "Create melding")
def test_create_melding(anyio_backend: str, test_database: None) -> None:
    pass
