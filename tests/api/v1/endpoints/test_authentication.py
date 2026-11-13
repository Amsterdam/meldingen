from datetime import timedelta
from typing import Annotated
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from httpx import AsyncClient
from jwt import PyJWKClient, PyJWT
from pytest import FixtureRequest
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from meldingen.authentication import is_authenticated_request
from meldingen.config import settings
from meldingen.dependencies import jwks_client
from meldingen.utils import utc_now


@pytest.fixture
def authentication_endpoint(app: FastAPI) -> str:
    async def authentication_status(
        authenticated: Annotated[bool, Depends(is_authenticated_request)],
    ) -> bool:
        return authenticated

    app.add_api_route("/test-authentication", authentication_status, methods=["GET"], name="test:authentication")
    return str(app.url_path_for("test:authentication"))


@pytest.fixture
def bearer_token(app: FastAPI, request: FixtureRequest) -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks_client_mock = Mock(PyJWKClient)
    jwks_client_mock.get_signing_key_from_jwt.return_value.key = private_key.public_key()

    def jwks_client_override() -> PyJWKClient:
        return jwks_client_mock

    app.dependency_overrides[jwks_client] = jwks_client_override

    payload = {
        "exp": utc_now() + timedelta(minutes=5),
        "aud": settings.auth_audience,
        "iss": settings.issuer_url,
        settings.auth_identifier_field: "user@example.com",
    }
    if hasattr(request, "param"):
        payload.update(request.param)

    return PyJWT().encode(payload, private_key, algorithm="RS256")


@pytest.mark.anyio
async def test_no_authorization_header(client: AsyncClient, authentication_endpoint: str) -> None:
    response = await client.get(authentication_endpoint)

    assert response.status_code == HTTP_200_OK
    is_authenticated_request = response.json()
    assert is_authenticated_request is False


@pytest.mark.anyio
async def test_valid_bearer_token(client: AsyncClient, authentication_endpoint: str, bearer_token: str) -> None:
    response = await client.get(authentication_endpoint, headers={"Authorization": f"Bearer {bearer_token}"})

    assert response.status_code == HTTP_200_OK
    is_authenticated_request = response.json()
    assert is_authenticated_request is True


@pytest.mark.anyio
@pytest.mark.parametrize("authorization", ["", "Bearer", "Bearer "])
async def test_authorization_header_without_token(
    client: AsyncClient, authentication_endpoint: str, authorization: str
) -> None:
    response = await client.get(authentication_endpoint, headers={"Authorization": authorization})

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "invalid_token"}


@pytest.mark.anyio
@pytest.mark.parametrize("authorization", ["Basic credentials", "Token credentials"])
async def test_malformed_authorization_scheme(
    client: AsyncClient, authentication_endpoint: str, authorization: str
) -> None:
    response = await client.get(authentication_endpoint, headers={"Authorization": authorization})

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "invalid_token"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("bearer_token", "status_code", "detail"),
    [
        pytest.param({"exp": 0}, HTTP_401_UNAUTHORIZED, "invalid_token", id="expired"),
        pytest.param({"aud": "invalid-audience"}, HTTP_401_UNAUTHORIZED, "invalid_token", id="invalid-audience"),
        pytest.param({"iss": "invalid-issuer"}, HTTP_401_UNAUTHORIZED, "invalid_token", id="invalid-issuer"),
        pytest.param(
            {settings.auth_identifier_field: None}, HTTP_400_BAD_REQUEST, "invalid_request", id="missing-identifier"
        ),
    ],
    indirect=["bearer_token"],
)
async def test_rejected_credentials(
    client: AsyncClient,
    authentication_endpoint: str,
    bearer_token: str,
    status_code: int,
    detail: str,
) -> None:
    response = await client.get(authentication_endpoint, headers={"Authorization": f"Bearer {bearer_token}"})

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
