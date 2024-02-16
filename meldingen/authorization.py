from casbin import AsyncEnforcer
from fastapi import HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from meldingen.models import User


class Authorizer:
    enforcer: AsyncEnforcer

    def __init__(self, enforcer: AsyncEnforcer):
        self.enforcer = enforcer

    async def __call__(self, user: User, obj: str, action: str) -> None:
        authorized = False
        for group in user.groups:
            if self.enforcer.enforce(group.name, obj, action):
                authorized = True
                break

        if not authorized:
            raise HTTPException(HTTP_403_FORBIDDEN)
