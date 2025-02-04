from typing import Any, Final

from fastapi import FastAPI
from httpx import AsyncClient
from pytest_bdd import given, parsers, then, when
from starlette.status import HTTP_200_OK

from tests.scenarios.conftest import async_step

ROUTE_CONTACT_INFO_ADD: Final[str] = "melding:contact-add"
ROUTE_FINALIZE_CONTACT_INFO_ADD: Final[str] = "melding:add-contact-info"


@given(
    parsers.re(r'I have a phone number "(?P<phone_number>\+\d{6,14})" and an email address "(?P<email>\w+@\w+\.\w+)"'),
    target_fixture="contact_info",
)
def i_have_a_phone_number_and_an_email_address(phone_number: str, email: str) -> dict[str, Any]:
    return {"phone": phone_number, "email": email}


@when("I add the contact information to my melding", target_fixture="my_melding")
@async_step
async def i_add_the_contact_information_to_my_melding(
    app: FastAPI, client: AsyncClient, my_melding: dict[str, Any], token: str, contact_info: dict[str, str]
) -> dict[str, Any]:
    response = await client.post(
        app.url_path_for(ROUTE_CONTACT_INFO_ADD, melding_id=my_melding["id"]),
        params={"token": token},
        json=contact_info,
    )
    assert response.status_code == HTTP_200_OK

    body = response.json()
    assert isinstance(body, dict)

    return body


@then("the melding contains my contact information")
def the_melding_contains_my_contact_information(contact_info: dict[str, Any], my_melding: dict[str, Any]) -> None:
    assert contact_info["email"] == my_melding["email"]
    assert contact_info["phone"] == my_melding["phone"]


@when("I finalize adding my contact info by proceeding to the next step", target_fixture="my_melding")
@async_step
async def i_finalize_submitting_the_contact_info_to_my_melding(
    app: FastAPI, client: AsyncClient, my_melding: dict[str, Any], token: str
) -> dict[str, Any]:
    response = await client.put(
        app.url_path_for(ROUTE_FINALIZE_CONTACT_INFO_ADD, melding_id=my_melding["id"]), params={"token": token}
    )
    assert response.status_code == HTTP_200_OK

    body = response.json()
    assert isinstance(body, dict)

    return body
