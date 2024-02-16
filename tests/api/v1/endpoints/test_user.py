from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_401_UNAUTHORIZED

from meldingen.models import User

ROUTE_NAME_CREATE: Final[str] = "user:create"
ROUTE_NAME_LIST: Final[str] = "user:list"
ROUTE_NAME_RETRIEVE: Final[str] = "user:retrieve"
ROUTE_NAME_DELETE: Final[str] = "user:delete"


@pytest.mark.asyncio
async def test_create_user(app: FastAPI, client: AsyncClient, auth_user: None) -> None:
    response = await client.post(
        app.url_path_for(ROUTE_NAME_CREATE), json={"username": "meldingen_user", "email": "user@example.com"}
    )

    assert response.status_code == HTTP_201_CREATED

    data = response.json()
    assert data.get("id") == 1
    assert data.get("username") == "meldingen_user"
    assert data.get("email") == "user@example.com"


@pytest.mark.asyncio
async def test_create_user_unauthorized(app: FastAPI, client: AsyncClient) -> None:
    """Tests that a 401 response is given when no access token is provided through the Authorization header."""
    response = await client.post(
        app.url_path_for(ROUTE_NAME_CREATE), json={"username": "meldingen_user", "email": "user@example.com"}
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


#
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit, offset, expected_result",
    [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
)
async def test_list_users(
    app: FastAPI,
    client: AsyncClient,
    auth_user: None,
    limit: int,
    offset: int,
    expected_result: int,
    test_users: list[User],
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"limit": limit, "offset": offset})

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == expected_result


@pytest.mark.asyncio
async def test_list_users_unauthorized(app: FastAPI, client: AsyncClient) -> None:
    """Tests that a 401 response is given when no access token is provided through the Authorization header."""
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_username, user_email",
    [("username #1", "user-1@example.com"), ("username #2", "user-2@example.com")],
    indirect=True,
)
async def test_retrieve_user(app: FastAPI, client: AsyncClient, auth_user: None, test_user: User) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, user_id=test_user.id))

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data.get("id") == test_user.id
    assert data.get("username") == test_user.username
    assert data.get("email") == test_user.email


@pytest.mark.asyncio
async def test_retrieve_user_unauthorized(app: FastAPI, client: AsyncClient, test_user: User) -> None:
    """Tests that a 401 response is given when no access token is provided through the Authorization header."""
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, user_id=test_user.id))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_username, user_email",
    [("username #1", "user-1@example.com"), ("username #2", "user-2@example.com")],
    indirect=True,
)
async def test_delete_user(app: FastAPI, client: AsyncClient, auth_user: None, test_user: User) -> None:
    response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, user_id=test_user.id))

    assert response.status_code == HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_username, user_email",
    [
        ("username #1", "user-1@example.com"),
    ],
    indirect=True,
)
async def test_delete_user_unauthorized(app: FastAPI, client: AsyncClient, test_user: User) -> None:
    """Tests that a 401 response is given when no access token is provided through the Authorization header."""
    response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, user_id=test_user.id))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_username, user_email, new_data",
    [
        ("username #1", "user-1@example.com", {"username": "U. Ser"}),
        ("username #1", "user-1@example.com", {"email": "u.ser@example.com"}),
        ("username #1", "user-1@example.com", {"username": "U. Ser", "email": "u.ser@example.com"}),
    ],
    indirect=["user_username", "user_email"],
)
async def test_update_user(
    app: FastAPI, client: AsyncClient, auth_user: None, test_user: User, new_data: dict[str, str]
) -> None:
    response = await client.patch(app.url_path_for(ROUTE_NAME_DELETE, user_id=test_user.id), json=new_data)

    assert response.status_code == HTTP_200_OK

    data = response.json()

    for key, value in new_data.items():
        assert data.get(key) == value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_username, user_email, new_username, new_email",
    [
        ("username #1", "user-1@example.com", "U. Ser", "u.ser@example.com"),
    ],
    indirect=["user_username", "user_email"],
)
async def test_update_user_unauthorized(
    app: FastAPI, client: AsyncClient, test_user: User, new_username: str, new_email: str
) -> None:
    """Tests that a 401 response is given when no access token is provided through the Authorization header."""
    response = await client.patch(
        app.url_path_for(ROUTE_NAME_DELETE, user_id=test_user.id), json={"username": new_username, "email": new_email}
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"
