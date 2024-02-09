from fastapi import HTTPException
from jwt import decode, PyJWKClient
from sqlalchemy.exc import NoResultFound
from starlette.status import HTTP_401_UNAUTHORIZED

from meldingen.models import User

from meldingen.repositories import UserRepository


class UnauthenticatedException(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, detail=detail)


class Authenticator:
    jwks_client: PyJWKClient
    user_repository: UserRepository

    def __init__(self, jwks_client: PyJWKClient, user_repository: UserRepository) -> None:
        self.jwks_client = jwks_client
        self.user_repository = user_repository

    async def __call__(self, token: str) -> User:
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        payload = decode(token, signing_key.key, algorithms=["RS256"], audience='account')

        email = payload.get('email')
        if email is None:
            raise UnauthenticatedException("Invalid token")

        try:
            return self.user_repository.find_by_email(email)
        except NoResultFound:
            raise UnauthenticatedException("User not found")
