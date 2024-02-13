from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from meldingen_core.actions.user import UserCreateAction, UserListAction, UserRetrieveAction

from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import User, UserCreateInput

router = APIRouter()


@router.post("/", name="user:create")
@inject
async def create_user(
    user_input: UserCreateInput,
    action: UserCreateAction = Depends(Provide(Container.user_create_action)),
    user: User = Depends(authenticate_user),
) -> User:
    melding = User.model_validate(user_input)
    action(melding)

    return melding


@router.get("/", name="user:list", response_model=list[User])
@inject
async def list_users(
    pagination: dict[str, int | None] = Depends(pagination_params),
    action: UserListAction = Depends(Provide(Container.user_list_action)),
    user: User = Depends(authenticate_user),
) -> Any:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    users = action(limit=limit, offset=offset)

    return users


@router.get("/{user_id}", name="user:retrieve", response_model=User)
@inject
async def retrieve_user(
    user_id: int,
    action: UserRetrieveAction = Depends(Provide(Container.user_retrieve_action)),
    user: User = Depends(authenticate_user),
) -> Any:
    db_user = action(pk=user_id)

    if not db_user:
        raise HTTPException(status_code=404)

    return db_user
