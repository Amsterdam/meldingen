from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from jwt import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    MissingRequiredClaimError,
    PyJWKClient,
    PyJWT,
)
from sqlalchemy.exc import NoResultFound

from meldingen.authentication import (
    InvalidRequestException,
    InvalidTokenException,
    UnauthenticatedException,
    authenticate_user,
)
from meldingen.models import User
from meldingen.repositories import UserRepository


@pytest.mark.anyio
async def test_get_user_token_expired(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.side_effect = ExpiredSignatureError()

    with pytest.raises(InvalidTokenException) as exc_info:
        await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "invalid_token"


@pytest.mark.anyio
async def test_get_user_token_invalid_issuer(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.side_effect = InvalidIssuerError()

    with pytest.raises(InvalidTokenException) as exc_info:
        await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "invalid_token"


@pytest.mark.anyio
async def test_get_user_token_invalid_audience(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.side_effect = InvalidAudienceError()

    with pytest.raises(InvalidTokenException) as exc_info:
        await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "invalid_token"


@pytest.mark.anyio
async def test_get_user_token_missing_claim(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.side_effect = MissingRequiredClaimError(claim="email")

    with pytest.raises(InvalidRequestException) as exc_info:
        await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, Mock(UserRepository))

    assert exc_info.value.detail == "invalid_request"


@pytest.mark.anyio
async def test_get_user(app: FastAPI) -> None:
    py_jwt_mock = Mock(PyJWT)
    py_jwt_mock.decode.return_value = {"email": "user@example.com"}

    test_user = User(email="user@example.com", username="user")

    user_repository = Mock(UserRepository)
    user_repository.find_by_email_or_create.return_value = test_user

    user = await authenticate_user("123456789", Mock(PyJWKClient), py_jwt_mock, user_repository)

    assert user == test_user
