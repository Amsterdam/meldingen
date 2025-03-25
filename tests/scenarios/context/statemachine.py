from typing import Any, Final

from fastapi import FastAPI
from httpx import AsyncClient, Response
from meldingen_core.statemachine import MeldingTransitions
from pytest_bdd import parsers, then, when

from tests.scenarios.conftest import async_step

ROUTE_FINISH_ANSWERING_QUESTIONS: Final[str] = "melding:answer_questions"
ROUTE_FINISH_UPLOADING_ATTACHMENTS: Final[str] = "melding:add-attachments"
ROUTE_NAME_LOCATION_FINALIZE: Final[str] = "melding:submit-location"
ROUTE_FINALIZE_CONTACT_INFO_ADD: Final[str] = "melding:add-contact-info"
ROUTE_NAME_SUBMIT: Final[str] = "melding:submit"


TRANSITION_TO_ROUTE_MAP = {
    MeldingTransitions.ANSWER_QUESTIONS: ROUTE_FINISH_ANSWERING_QUESTIONS,
    MeldingTransitions.ADD_ATTACHMENTS: ROUTE_FINISH_UPLOADING_ATTACHMENTS,
    MeldingTransitions.SUBMIT_LOCATION: ROUTE_NAME_LOCATION_FINALIZE,
    MeldingTransitions.ADD_CONTACT_INFO: ROUTE_FINALIZE_CONTACT_INFO_ADD,
    MeldingTransitions.SUBMIT: ROUTE_NAME_SUBMIT,
}


@when(parsers.parse('I finish my current step by completing "{transition:w}"'), target_fixture="api_response")
@async_step
async def finalize_current_step_and_proceeding_to(
    app: FastAPI, client: AsyncClient, my_melding: dict[str, Any], token: str, transition: str
) -> Response:
    transition_enum = MeldingTransitions[transition]
    route = TRANSITION_TO_ROUTE_MAP.get(transition_enum, False)
    assert route

    response = await client.put(app.url_path_for(route, melding_id=my_melding["id"]), params={"token": token})

    return response


@then(parsers.parse('the state of the melding should be "{state:w}"'))
def the_state_of_the_melding_should_be(my_melding: dict[str, Any], state: str) -> None:
    assert state == my_melding.get("state")
