from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from jwt import ExpiredSignatureError, PyJWKClient, PyJWT
from sqlalchemy.exc import NoResultFound

from meldingen.authentication import UnauthenticatedException, authenticate_user
from meldingen.models import User
from meldingen.repositories import UserRepository


@pytest.mark.anyio
async def test_get_user_token_expired(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.side_effect = ExpiredSignatureError()

    with pytest.raises(UnauthenticatedException) as exc_info:
        await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "Token has expired"


@pytest.mark.anyio
async def test_get_user_token_invalid(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.return_value = {}

    with pytest.raises(UnauthenticatedException) as exc_info:
        await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "Invalid token"


@pytest.mark.anyio
async def test_get_user_not_found(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.return_value = {"email": "a@b.c"}

    user_repository = Mock(UserRepository)
    user_repository.find_by_email.side_effect = NoResultFound()

    with pytest.raises(UnauthenticatedException) as exc_info:
        await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, user_repository)

    assert exc_info.value.detail == "User not found"


@pytest.mark.anyio
async def test_get_user(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.return_value = {"email": "user@example.com"}

    test_user = User(email="user@example.com", username="user")

    user_repository = Mock(UserRepository)
    user_repository.find_by_email.return_value = test_user

    user = await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, user_repository)

    assert user == test_user
