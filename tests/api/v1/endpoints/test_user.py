from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import User

ROUTE_NAME_CREATE: Final[str] = "user:create"
ROUTE_NAME_LIST: Final[str] = "user:list"
ROUTE_NAME_RETRIEVE: Final[str] = "user:retrieve"
ROUTE_NAME_DELETE: Final[str] = "user:delete"
ROUTE_NAME_UPDATE: Final[str] = "user:update"


class TestUserCreate:
    @pytest.mark.asyncio
    async def test_create_user(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(
            app.url_path_for(ROUTE_NAME_CREATE), json={"username": "meldingen_user", "email": "user@example.com"}
        )

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") == 1
        assert data.get("username") == "meldingen_user"
        assert data.get("email") == "user@example.com"

    @pytest.mark.asyncio
    async def test_create_user_username_minimum_length_violation(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE_NAME_CREATE), json={"username": "", "email": "user@example.com"}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "string_too_short"
        assert violation.get("loc") == ["body", "username"]
        assert violation.get("msg") == "String should have at least 3 characters"

    @pytest.mark.asyncio
    async def test_create_user_email_violation(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(
            app.url_path_for(ROUTE_NAME_CREATE), json={"username": "meldingen_user", "email": "user.example.com"}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "value_error"
        assert violation.get("loc") == ["body", "email"]
        assert (
            violation.get("msg")
            == "value is not a valid email address: The email address is not valid. It must have exactly one @-sign."
        )

    @pytest.mark.asyncio
    async def test_create_user_unauthorized(self, app: FastAPI, client: AsyncClient) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.post(
            app.url_path_for(ROUTE_NAME_CREATE), json={"username": "meldingen_user", "email": "user@example.com"}
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_username, user_email, new_username, new_email",
        [
            ("username #1", "user-1@example.com", "username #1", "user-2@example.com"),
            ("username #1", "user-1@example.com", "username #2", "user-1@example.com"),
            ("username #1", "user-1@example.com", "username #1", "user-1@example.com"),
        ],
        indirect=["user_username", "user_email"],
    )
    async def test_create_existing_user_invalid(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User, new_username: str, new_email: str
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE_NAME_CREATE), json={"username": new_username, "email": new_email}
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )


class TestUserList:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, expected_result",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_users(
        self,
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
    async def test_list_users_unauthorized(self, app: FastAPI, client: AsyncClient) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.get(app.url_path_for(ROUTE_NAME_LIST))

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, type, msg",
        [
            ("abc", "int_parsing", "Input should be a valid integer, unable to parse string as an integer"),
            (-1, "greater_than_equal", "Input should be greater than or equal to 0"),
        ],
    )
    async def test_list_users_invalid_limit(
        self, app: FastAPI, client: AsyncClient, auth_user: None, limit: str | int, type: str, msg: str
    ) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"limit": limit})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == type
        assert violation.get("loc") == ["query", "limit"]
        assert violation.get("msg") == msg

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "offset, type, msg",
        [
            ("abc", "int_parsing", "Input should be a valid integer, unable to parse string as an integer"),
            (-1, "greater_than_equal", "Input should be greater than or equal to 0"),
        ],
    )
    async def test_list_users_invalid_offset(
        self, app: FastAPI, client: AsyncClient, auth_user: None, offset: str | int, type: str, msg: str
    ) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"offset": offset})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == type
        assert violation.get("loc") == ["query", "offset"]
        assert violation.get("msg") == msg


class TestUserRetrieve:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_username, user_email",
        [("username #1", "user-1@example.com"), ("username #2", "user-2@example.com")],
        indirect=True,
    )
    async def test_retrieve_user(self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, user_id=test_user.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == test_user.id
        assert data.get("username") == test_user.username
        assert data.get("email") == test_user.email

    @pytest.mark.asyncio
    async def test_retrieve_user_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, user_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_retrieve_user_unauthorized(self, app: FastAPI, client: AsyncClient, test_user: User) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, user_id=test_user.id))

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"


class TestUserDelete:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_username, user_email",
        [("username #1", "user-1@example.com"), ("username #2", "user-2@example.com")],
        indirect=True,
    )
    async def test_delete_user(self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User) -> None:
        response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, user_id=test_user.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_user_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, user_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_delete_user_own_user(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, user_id=400))

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()
        assert body.get("detail") == "You cannot delete your own account"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_username, user_email",
        [
            ("username #1", "user-1@example.com"),
        ],
        indirect=True,
    )
    async def test_delete_user_unauthorized(self, app: FastAPI, client: AsyncClient, test_user: User) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, user_id=test_user.id))

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"


class TestUserUpdate:
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
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User, new_data: dict[str, str]
    ) -> None:
        response = await client.patch(app.url_path_for(ROUTE_NAME_UPDATE, user_id=test_user.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for key, value in new_data.items():
            assert data.get(key) == value

    @pytest.mark.asyncio
    async def test_update_user_username_minimum_length_violation(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User
    ) -> None:
        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, user_id=test_user.id), json={"username": "ab"}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "string_too_short"
        assert violation.get("loc") == ["body", "username"]
        assert violation.get("msg") == "String should have at least 3 characters"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_data",
        [
            ({"username": 1234}),
            ({"email": "not an email"}),
            ({"username": ["user", 1], "email": True}),
        ],
    )
    async def test_update_user_invalid_data(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User, invalid_data: dict[str, str]
    ) -> None:
        response = await client.patch(app.url_path_for(ROUTE_NAME_UPDATE, user_id=test_user.id), json=invalid_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_non_existing_user(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, user_id=999), json={"username": "test", "email": "test@example.com"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_username, user_email, new_username, new_email",
        [
            ("username #1", "user-1@example.com", "U. Ser", "u.ser@example.com"),
        ],
        indirect=["user_username", "user_email"],
    )
    async def test_update_user_unauthorized(
        self, app: FastAPI, client: AsyncClient, test_user: User, new_username: str, new_email: str
    ) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, user_id=test_user.id),
            json={"username": new_username, "email": new_email},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "new_username, new_email",
        [
            ("test_user_2", "test_email_1@example.com"),
            ("test_user_1", "test_email_2@example.com"),
            ("test_user_2", "test_email_2@example.com"),
        ],
    )
    async def test_update_to_existing_user_invalid(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        test_users: list[User],
        new_username: str,
        new_email: str,
    ) -> None:
        test_user = test_users[0]

        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, user_id=test_user.id),
            json={"username": new_username, "email": new_email},
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )
