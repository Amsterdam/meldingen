from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from jwt import ExpiredSignatureError

from meldingen.authentication import UnauthenticatedException, get_user
from meldingen.models import User


@pytest.mark.asyncio
async def test_get_user_token_expired(app: FastAPI, py_jwt_mock: Mock) -> None:
    py_jwt_mock.decode.side_effect = ExpiredSignatureError()

    with pytest.raises(UnauthenticatedException) as exc_info:
        await get_user("123456789")

    assert exc_info.value.detail == "Token has expired"


@pytest.mark.asyncio
async def test_get_user_token_invalid(app: FastAPI, py_jwt_mock: Mock) -> None:
    py_jwt_mock.decode.return_value = {}

    with pytest.raises(UnauthenticatedException) as exc_info:
        await get_user("123456789")

    assert exc_info.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_get_user_not_found(app: FastAPI, py_jwt_mock: Mock) -> None:
    py_jwt_mock.decode.return_value = {"email": "a@b.c"}

    with pytest.raises(UnauthenticatedException) as exc_info:
        await get_user("123456789")

    assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio
async def test_get_user(app: FastAPI, py_jwt_mock: Mock, test_user: User) -> None:
    py_jwt_mock.decode.return_value = {"email": "user@example.com"}

    user = await get_user("123456789")

    assert user == test_user
