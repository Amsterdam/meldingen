from pytest_bdd import scenario

from tests.scenarios.context.asset import *  # noqa
from tests.scenarios.context.attachment import *  # noqa
from tests.scenarios.context.classification import *  # noqa
from tests.scenarios.context.contact import *  # noqa
from tests.scenarios.context.form import *  # noqa
from tests.scenarios.context.location import *  # noqa
from tests.scenarios.context.mail import *  # noqa
from tests.scenarios.context.melding import *  # noqa
from tests.scenarios.context.statemachine import *  # noqa


@scenario("create_melding.feature", "A melder successfully submits a melding")
def test_create_melding(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melding can't be submitted without a valid location")
def test_cant_submit_melding_without_location(anyio_backend: str, test_database: None) -> None:
    pass


@scenario(
    "create_melding.feature", "A melding can't be submitted if not all required additional questions are answered"
)
def test_must_answer_all_required_additional_questions(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melding in the state classified can't skip any steps")
def test_melding_classified_cant_skip_steps(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melding in the state questions_answered can't skip any steps")
def test_melding_questions_answered_cant_skip_steps(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melding in the state attachments_added can't skip any steps")
def test_melding_attachments_added_cant_skip_steps(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melding in the state location_submitted can't skip any steps")
def test_melding_location_submitted_cant_skip_steps(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melding in the state contact_info_added can go back to all previous states")
def test_melding_contact_info_added_can_go_back(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melding that has been submitted can not go back to a previous state")
def test_melding_submitted_can_not_go_back(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melder can add an asset to a melding")
def test_add_asset_to_melding(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melder cannot exceed max_assets limit")
def test_cannot_exceed_max_assets(anyio_backend: str, test_database: None) -> None:
    pass


@scenario("create_melding.feature", "A melder can add an asset after removing one when at max_assets")
def test_add_asset_after_removal(anyio_backend: str, test_database: None) -> None:
    pass
