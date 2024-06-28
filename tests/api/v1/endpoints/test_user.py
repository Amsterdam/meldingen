from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import User
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestUserCreate(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "user:create"
    METHOD: Final[str] = "POST"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
    async def test_create_user(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME), json={"username": "meldingen_user", "email": "user@example.com"}
        )

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") == 1
        assert data.get("username") == "meldingen_user"
        assert data.get("email") == "user@example.com"
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.asyncio
    async def test_create_user_username_minimum_length_violation(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME), json={"username": "", "email": "user@example.com"}
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
            app.url_path_for(self.ROUTE_NAME), json={"username": "meldingen_user", "email": "user.example.com"}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "value_error"
        assert violation.get("loc") == ["body", "email"]
        assert violation.get("msg") == "value is not a valid email address: An email address must have an @-sign."

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
            app.url_path_for(self.ROUTE_NAME), json={"username": new_username, "email": new_email}
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )


class TestUserList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    ROUTE_NAME: Final[str] = "user:list"
    METHOD: Final[str] = "GET"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, expected_result",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_users_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected_result: int,
        test_users: list[User],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        assert response.headers.get("content-range") == f"user {offset}-{limit - 1 + offset}/10"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "id",
                SortingDirection.ASC,
                [
                    {"id": 1, "email": "test_email_0@example.com", "username": "test_user_0"},
                    {"id": 2, "email": "test_email_1@example.com", "username": "test_user_1"},
                    {"id": 3, "email": "test_email_2@example.com", "username": "test_user_2"},
                    {"id": 4, "email": "test_email_3@example.com", "username": "test_user_3"},
                    {"id": 5, "email": "test_email_4@example.com", "username": "test_user_4"},
                    {"id": 6, "email": "test_email_5@example.com", "username": "test_user_5"},
                    {"id": 7, "email": "test_email_6@example.com", "username": "test_user_6"},
                    {"id": 8, "email": "test_email_7@example.com", "username": "test_user_7"},
                    {"id": 9, "email": "test_email_8@example.com", "username": "test_user_8"},
                    {"id": 10, "email": "test_email_9@example.com", "username": "test_user_9"},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"id": 10, "email": "test_email_9@example.com", "username": "test_user_9"},
                    {"id": 9, "email": "test_email_8@example.com", "username": "test_user_8"},
                    {"id": 8, "email": "test_email_7@example.com", "username": "test_user_7"},
                    {"id": 7, "email": "test_email_6@example.com", "username": "test_user_6"},
                    {"id": 6, "email": "test_email_5@example.com", "username": "test_user_5"},
                    {"id": 5, "email": "test_email_4@example.com", "username": "test_user_4"},
                    {"id": 4, "email": "test_email_3@example.com", "username": "test_user_3"},
                    {"id": 3, "email": "test_email_2@example.com", "username": "test_user_2"},
                    {"id": 2, "email": "test_email_1@example.com", "username": "test_user_1"},
                    {"id": 1, "email": "test_email_0@example.com", "username": "test_user_0"},
                ],
            ),
            (
                "username",
                SortingDirection.ASC,
                [
                    {"id": 1, "email": "test_email_0@example.com", "username": "test_user_0"},
                    {"id": 2, "email": "test_email_1@example.com", "username": "test_user_1"},
                    {"id": 3, "email": "test_email_2@example.com", "username": "test_user_2"},
                    {"id": 4, "email": "test_email_3@example.com", "username": "test_user_3"},
                    {"id": 5, "email": "test_email_4@example.com", "username": "test_user_4"},
                    {"id": 6, "email": "test_email_5@example.com", "username": "test_user_5"},
                    {"id": 7, "email": "test_email_6@example.com", "username": "test_user_6"},
                    {"id": 8, "email": "test_email_7@example.com", "username": "test_user_7"},
                    {"id": 9, "email": "test_email_8@example.com", "username": "test_user_8"},
                    {"id": 10, "email": "test_email_9@example.com", "username": "test_user_9"},
                ],
            ),
            (
                "username",
                SortingDirection.DESC,
                [
                    {"id": 10, "email": "test_email_9@example.com", "username": "test_user_9"},
                    {"id": 9, "email": "test_email_8@example.com", "username": "test_user_8"},
                    {"id": 8, "email": "test_email_7@example.com", "username": "test_user_7"},
                    {"id": 7, "email": "test_email_6@example.com", "username": "test_user_6"},
                    {"id": 6, "email": "test_email_5@example.com", "username": "test_user_5"},
                    {"id": 5, "email": "test_email_4@example.com", "username": "test_user_4"},
                    {"id": 4, "email": "test_email_3@example.com", "username": "test_user_3"},
                    {"id": 3, "email": "test_email_2@example.com", "username": "test_user_2"},
                    {"id": 2, "email": "test_email_1@example.com", "username": "test_user_1"},
                    {"id": 1, "email": "test_email_0@example.com", "username": "test_user_0"},
                ],
            ),
        ],
    )
    async def test_list_users_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        test_users: list[User],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME), params={"sort": f'["{attribute}", "{direction}"]'}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["id"] == expected[i]["id"]
            assert data[i]["email"] == expected[i]["email"]
            assert data[i]["username"] == expected[i]["username"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == "user 0-49/10"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, attribute, direction, expected",
        [
            (
                2,
                2,
                "username",
                SortingDirection.DESC,
                [
                    {"id": 8, "email": "test_email_7@example.com", "username": "test_user_7"},
                    {"id": 7, "email": "test_email_6@example.com", "username": "test_user_6"},
                ],
            ),
            (
                3,
                1,
                "username",
                SortingDirection.ASC,
                [
                    {"id": 2, "email": "test_email_1@example.com", "username": "test_user_1"},
                    {"id": 3, "email": "test_email_2@example.com", "username": "test_user_2"},
                    {"id": 4, "email": "test_email_3@example.com", "username": "test_user_3"},
                ],
            ),
        ],
    )
    async def test_list_users_paginated_and_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        test_users: list[User],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME),
            params={"limit": limit, "offset": offset, "sort": f'["{attribute}", "{direction}"]'},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["id"] == expected[i]["id"]
            assert data[i]["email"] == expected[i]["email"]
            assert data[i]["username"] == expected[i]["username"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == f"user {offset}-{limit - 1 + offset}/10"


class TestUserRetrieve(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "user:retrieve"
    METHOD: Final[str] = "GET"
    PATH_PARAMS: dict[str, Any] = {"user_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_username, user_email",
        [("username #1", "user-1@example.com"), ("username #2", "user-2@example.com")],
        indirect=True,
    )
    async def test_retrieve_user(self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, user_id=test_user.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == test_user.id
        assert data.get("username") == test_user.username
        assert data.get("email") == test_user.email
        assert data.get("created_at") == test_user.created_at.isoformat()
        assert data.get("updated_at") == test_user.updated_at.isoformat()

    @pytest.mark.asyncio
    async def test_retrieve_user_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, user_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class TestUserDelete(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "user:delete"
    METHOD: Final[str] = "DELETE"
    PATH_PARAMS: dict[str, Any] = {"user_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_username, user_email",
        [("username #1", "user-1@example.com"), ("username #2", "user-2@example.com")],
        indirect=True,
    )
    async def test_delete_user(self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, user_id=test_user.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_user_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, user_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_delete_user_own_user(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, user_id=400))

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()
        assert body.get("detail") == "You cannot delete your own account"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("user_id", [0, -1])
    async def test_delete_invalid_id(self, app: FastAPI, client: AsyncClient, auth_user: None, user_id: int) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, user_id=user_id))

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "greater_than_equal"
        assert violation.get("loc") == ["path", "user_id"]
        assert violation.get("msg") == "Input should be greater than or equal to 1"


class TestUserUpdate(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "user:update"
    METHOD: Final[str] = "PATCH"
    PATH_PARAMS: dict[str, Any] = {"user_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

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
        response = await client.patch(app.url_path_for(self.ROUTE_NAME, user_id=test_user.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for key, value in new_data.items():
            assert data.get(key) == value

        assert data.get("created_at") == test_user.created_at.isoformat()
        assert data.get("updated_at") == test_user.updated_at.isoformat()

    @pytest.mark.asyncio
    async def test_update_user_username_minimum_length_violation(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_user: User
    ) -> None:
        response = await client.patch(app.url_path_for(self.ROUTE_NAME, user_id=test_user.id), json={"username": "ab"})

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
        response = await client.patch(app.url_path_for(self.ROUTE_NAME, user_id=test_user.id), json=invalid_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_non_existing_user(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, user_id=999), json={"username": "test", "email": "test@example.com"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

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
            app.url_path_for(self.ROUTE_NAME, user_id=test_user.id),
            json={"username": new_username, "email": new_email},
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )
