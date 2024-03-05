from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_401_UNAUTHORIZED,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import Classification

ROUTE_NAME_CREATE: Final[str] = "classification:create"
ROUTE_NAME_LIST: Final[str] = "classification:list"
ROUTE_NAME_RETRIEVE: Final[str] = "classification:retrieve"
ROUTE_NAME_UPDATE: Final[str] = "classification:update"
ROUTE_NAME_DELETE: Final[str] = "classification:delete"


@pytest.mark.asyncio
async def test_create_classification(app: FastAPI, client: AsyncClient, auth_user: None) -> None:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"name": "bla"})

    assert response.status_code == HTTP_201_CREATED

    data = response.json()
    assert data.get("id") == 1
    assert data.get("name") == "bla"


@pytest.mark.asyncio
async def test_create_classification_unauthorized(app: FastAPI, client: AsyncClient) -> None:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"name": "bla"})

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
async def test_create_classification_name_min_length_violation(
    app: FastAPI, client: AsyncClient, auth_user: None
) -> None:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"name": ""})

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    detail = data.get("detail")
    assert len(detail) == 1

    violation = detail[0]
    assert violation.get("type") == "string_too_short"
    assert violation.get("loc") == ["body", "name"]
    assert violation.get("msg") == "String should have at least 1 character"


@pytest.mark.asyncio
@pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
async def test_create_classification_duplicate_name(
    app: FastAPI, client: AsyncClient, auth_user: None, classification: Classification
) -> None:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"name": "bla"})

    assert response.status_code == HTTP_409_CONFLICT

    data = response.json()
    assert data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."


@pytest.mark.asyncio
async def test_list_all_classifications(
    app: FastAPI, client: AsyncClient, auth_user: None, classifications: list[Classification]
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST))

    assert response.status_code == HTTP_200_OK

    data = response.json()

    assert len(data) == len(classifications)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit, offset, expected",
    [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
)
async def test_list_classifications(
    app: FastAPI,
    client: AsyncClient,
    auth_user: None,
    limit: int,
    offset: int,
    expected: int,
    classifications: list[Classification],
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"limit": limit, "offset": offset})

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == expected


@pytest.mark.asyncio
async def test_list_classifications_unauthorized(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
@pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
async def test_retrieve_classification(
    app: FastAPI, client: AsyncClient, auth_user: None, classification: Classification
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, classification_id=classification.id))

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data.get("id") == 1
    assert data.get("name") == "bla"


@pytest.mark.asyncio
@pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
async def test_retrieve_classification_unauthorized(
    app: FastAPI, client: AsyncClient, classification: Classification
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, classification_id=classification.id))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
@pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
async def test_update_classification(
    app: FastAPI, client: AsyncClient, classification: Classification, auth_user: None
) -> None:
    response = await client.patch(
        app.url_path_for(ROUTE_NAME_UPDATE, classification_id=classification.id), json={"name": "bladiebla"}
    )

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data.get("name") == "bladiebla"


@pytest.mark.asyncio
@pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
async def test_update_classification_unauthorized(
    app: FastAPI, client: AsyncClient, classification: Classification
) -> None:
    response = await client.patch(
        app.url_path_for(ROUTE_NAME_UPDATE, classification_id=classification.id), json={"name": "bladiebla"}
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
async def test_update_classification_duplicate_name(
    app: FastAPI, client: AsyncClient, classifications: list[Classification], auth_user: None
) -> None:
    response = await client.patch(
        app.url_path_for(ROUTE_NAME_UPDATE, classification_id=1), json={"name": "category: 2"}
    )

    assert response.status_code == HTTP_409_CONFLICT

    data = response.json()
    assert data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."


@pytest.mark.asyncio
@pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
async def test_delete_classification(
    app: FastAPI, client: AsyncClient, classification: Classification, auth_user: None
) -> None:
    response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, classification_id=classification.id))

    assert response.status_code == HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
async def test_delete_classification_unauthorized(
    app: FastAPI, client: AsyncClient, classification: Classification
) -> None:
    response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, classification_id=classification.id))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"
