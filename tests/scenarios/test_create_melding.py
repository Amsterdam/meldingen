import pytest
from pytest_bdd import scenario
from tests.scenarios.context.create_melding import * # noqa

@scenario(
    'create_melding.feature',
    'Create a melding',
)
@pytest.mark.anyio
def test_create_melding() -> None:
    pass
