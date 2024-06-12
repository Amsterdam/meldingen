# from dependency_injector.wiring import Provide, inject
# from fastapi import Depends, HTTPException
# from fastapi.security import OAuth2AuthorizationCodeBearer
# from jwt import ExpiredSignatureError, PyJWKClient, PyJWT
# from sqlalchemy.exc import NoResultFound
# from starlette.status import HTTP_401_UNAUTHORIZED
#
# from meldingen.config import settings
# from meldingen.models import User
# from meldingen.repositories import UserRepository
#
# oauth2_scheme = OAuth2AuthorizationCodeBearer(
#     settings.auth_url,
#     settings.token_url,
# )
#
#
# class UnauthenticatedException(HTTPException):
#     def __init__(self, detail: str) -> None:
#         super().__init__(status_code=HTTP_401_UNAUTHORIZED, detail=detail)
#
#
# @inject
# async def get_user(
#     token: str,
#     jwks_client: PyJWKClient = Provide["jwks_client"],
#     py_jwt: PyJWT = Provide["py_jwt"],
#     user_repository: UserRepository = Provide["user_repository"],
# ) -> User:
#     signing_key = jwks_client.get_signing_key_from_jwt(token)
#
#     try:
#         payload = py_jwt.decode(token, signing_key.key, algorithms=["RS256"], audience="account")
#     except ExpiredSignatureError:
#         raise UnauthenticatedException("Token has expired")
#
#     email = payload.get("email")
#     if email is None:
#         raise UnauthenticatedException("Invalid token")
#
#     try:
#         return await user_repository.find_by_email(email)
#     except NoResultFound:
#         raise UnauthenticatedException("User not found")
#
#
# async def authenticate_user(token: str = Depends(oauth2_scheme)) -> User:
#     return await get_user(token)  # pragma: no cover
