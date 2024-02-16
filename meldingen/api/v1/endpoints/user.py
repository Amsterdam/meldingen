from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from meldingen_core.actions.user import (
    UserCreateAction,
    UserDeleteAction,
    UserListAction,
    UserRetrieveAction,
    UserUpdateAction,
)
from sqlalchemy.exc import NoResultFound

from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import User, UserInput, UserPartialInput

router = APIRouter()


@router.post("/", name="user:create", status_code=201)
@inject
async def create_user(
    user_input: UserInput,
    action: UserCreateAction = Depends(Provide(Container.user_create_action)),
    user: User = Depends(authenticate_user),
) -> User:
    melding = User.model_validate(user_input)
    await action(melding)

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

    users = await action(limit=limit, offset=offset)

    return users


@router.get("/{user_id}", name="user:retrieve", response_model=User)
@inject
async def retrieve_user(
    user_id: int,
    action: UserRetrieveAction = Depends(Provide(Container.user_retrieve_action)),
    user: User = Depends(authenticate_user),
) -> Any:
    db_user = await action(pk=user_id)
    if not db_user:
        raise HTTPException(status_code=404)

    return db_user


@router.delete("/{user_id}", name="user:delete", status_code=204)
@inject
async def delete_user(
    user_id: int,
    action: UserDeleteAction = Depends(Provide(Container.user_delete_action)),
    user: User = Depends(authenticate_user),
) -> None:
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    try:
        await action(pk=user_id)
    except NoResultFound:
        raise HTTPException(status_code=404)


@router.patch("/{user_id}", name="user:update", response_model=User)
@inject
async def update_user(
    user_id: int,
    user_input: UserPartialInput,
    retrieve_action: UserRetrieveAction = Depends(Provide(Container.user_retrieve_action)),
    update_action: UserUpdateAction = Depends(Provide(Container.user_create_action)),
    user: User = Depends(authenticate_user),
) -> Any:
    db_user = await retrieve_action(pk=user_id)
    if not db_user:
        raise HTTPException(status_code=404)

    user_data = user_input.model_dump(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)

    await update_action(db_user)

    return db_user
