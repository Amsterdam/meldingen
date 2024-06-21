from unittest.mock import Mock

import pytest
from jwt import ExpiredSignatureError, PyJWKClient, PyJWT
from sqlalchemy.exc import NoResultFound

from meldingen.authentication import UnauthenticatedException, get_user
from meldingen.models import User
from meldingen.repositories import UserRepository


@pytest.mark.asyncio
async def test_get_user_token_expired() -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.side_effect = ExpiredSignatureError()

    with pytest.raises(UnauthenticatedException) as exc_info:
        await get_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "Token has expired"


@pytest.mark.asyncio
async def test_get_user_token_invalid() -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.return_value = {}

    with pytest.raises(UnauthenticatedException) as exc_info:
        await get_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_get_user_not_found() -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.return_value = {"email": "a@b.c"}

    user_repository_mock = Mock(UserRepository)
    user_repository_mock.find_by_email.side_effect = NoResultFound()

    with pytest.raises(UnauthenticatedException) as exc_info:
        await get_user("123456789", Mock(PyJWKClient), py_jwt_mock, user_repository_mock)

    assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio
async def test_get_user() -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.return_value = {"email": "user@example.com"}

    test_user = User("user@example.com", "user@example.com")

    user_repository_mock = Mock(UserRepository)
    user_repository_mock.find_by_email.return_value = test_user

    user = await get_user("123456789", Mock(PyJWKClient), py_jwt_mock, user_repository_mock)

    assert user == test_user
