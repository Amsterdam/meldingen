from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from jwt import ExpiredSignatureError

from meldingen.authentication import UnauthenticatedException, get_user


@pytest.mark.asyncio
async def test_get_user_token_expired(app: FastAPI, py_jwt_mock: Mock) -> None:
    py_jwt_mock.decode.side_effect = ExpiredSignatureError()

    with pytest.raises(UnauthenticatedException):
        await get_user("123456789")
