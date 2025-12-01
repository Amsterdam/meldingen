from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    MissingRequiredClaimError,
    PyJWKClient,
    PyJWT,
)
from sqlalchemy.exc import NoResultFound
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from meldingen.config import settings
from meldingen.dependencies import jwks_client, py_jwt, user_repository
from meldingen.models import User
from meldingen.repositories import UserRepository

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    settings.auth_url,
    settings.token_url,
)


class UnauthenticatedException(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, detail=detail)


class InvalidRequestException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=HTTP_400_BAD_REQUEST, detail="invalid_request")


class InvalidTokenException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, detail="invalid_token")


async def authenticate_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    jwks_client: Annotated[PyJWKClient, Depends(jwks_client)],
    py_jwt: Annotated[PyJWT, Depends(py_jwt)],
    user_repository: Annotated[UserRepository, Depends(user_repository)],
) -> User:
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    try:
        payload = py_jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.auth_audience,
            issuer=settings.issuer_url,
            options={"require": ["exp", "aud", "iss", settings.auth_identifier_field]},
        )
    except (ExpiredSignatureError, InvalidIssuerError, InvalidAudienceError):
        raise InvalidTokenException()
    except MissingRequiredClaimError:
        raise InvalidRequestException()

    email = payload.get(settings.auth_identifier_field)

    try:
        return await user_repository.find_by_email(email)
    except NoResultFound:
        raise UnauthenticatedException("User not found")
