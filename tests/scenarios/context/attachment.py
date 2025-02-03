from os import path
from typing import Any, Final

from fastapi import FastAPI
from httpx import AsyncClient
from pytest_bdd import given, parsers, then, when
from starlette.status import HTTP_200_OK

from tests.conftest import malware_scanner_override
from tests.scenarios.conftest import async_step

ROUTE_ADD_ATTACHMENTS: Final[str] = "melding:attachment"
ROUTE_FINISH_UPLOADING_ATTACHMENTS: Final[str] = "melding:add-attachments"
ROUTE_MELDING_LIST_ATTACHMENTS: Final[str] = "melding:attachments"


@given(
    parsers.re(r'I have a file "(?P<filename>.*\.(jpg|png|webp))" that I want to attach to the melding'),
    target_fixture="filename",
)
def i_have_a_file_with_the_name(filename: str) -> str:
    return filename


@given("it is in my file system", target_fixture="filepath")
def it_is_in_my_filesystem(filename: str) -> str:
    filepath = path.join(
        path.abspath(path.dirname(path.dirname(path.dirname(__file__)))),
        "resources",
        filename,
    )
    assert path.exists(filepath)
    return filepath


@when("I upload the file", target_fixture="upload_response")
@async_step
async def upload_the_file(
    app: FastAPI,
    client: AsyncClient,
    malware_scanner_override: None,
    filepath: str,
    filename: str,
    create_melding_response_body: dict[str, Any],
) -> dict[str, Any]:
    melding_id, token = create_melding_response_body["id"], create_melding_response_body["token"]

    response = await client.post(
        app.url_path_for(ROUTE_ADD_ATTACHMENTS, melding_id=melding_id),
        params={"token": token},
        files={
            "file": open(
                filepath,
                "rb",
            )
        },
        # We have to provide the header and boundary manually, otherwise httpx will set the content-type
        # to application/json and the request will fail.
        headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
    )

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert isinstance(body, dict)

    assert body["original_filename"] == filename
    return body


@then("the upload response should include data about my file as attachment", target_fixture="attachment_id")
def the_upload_response_should_include_data_about_my_file(
    upload_response: dict[str, Any], filename: str, filepath: str
) -> int:
    assert upload_response["original_filename"] == filename
    assert isinstance(upload_response["id"], int)

    return upload_response["id"]


@when("I check the attachments of my melding", target_fixture="melding_attachments")
@async_step
async def i_check_the_attachments_of_my_melding(
    app: FastAPI, client: AsyncClient, create_melding_response_body: dict[str, Any]
) -> list[dict[str, Any]]:
    melding_id, token = create_melding_response_body["id"], create_melding_response_body["token"]

    response = await client.get(
        app.url_path_for(ROUTE_MELDING_LIST_ATTACHMENTS, melding_id=melding_id),
        params={"token": token},
    )

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert isinstance(body, list)

    return body


@then(parsers.parse("there should be {count:d} attachments"))
def there_should_be_attachments(melding_attachments: list[dict[str, Any]], count: int) -> None:
    assert len(melding_attachments) == count


@then("the attachments should contain my file")
def the_attachments_should_contain_my_file(
    melding_attachments: list[dict[str, Any]], filename: str, filepath: str, attachment_id: int
) -> None:
    attachment = melding_attachments[0]

    assert attachment["original_filename"] == filename
    assert attachment["id"] == attachment_id


@when("I am finished with adding attachments", target_fixture="melding_after_uploading_attachments")
@async_step
async def i_have_finished_uploading_my_files(
    app: FastAPI, client: AsyncClient, create_melding_response_body: dict[str, Any]
) -> dict[str, Any]:
    melding = create_melding_response_body

    response = await client.put(
        app.url_path_for(ROUTE_FINISH_UPLOADING_ATTACHMENTS, melding_id=melding["id"]),
        params={"token": melding["token"]},
    )

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert isinstance(body, dict)

    return body


@then(parsers.parse('the melding state should be "{state:w}"'))
def i_expect_the_melding_state_to_be(melding_after_uploading_attachments: dict[str, Any], state: str) -> None:
    assert melding_after_uploading_attachments["state"] == state
