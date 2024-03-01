from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path
from meldingen_core.actions.user import UserCreateAction, UserDeleteAction
from meldingen_core.exceptions import NotFoundException
from sqlalchemy.exc import NoResultFound

from meldingen.actions import UserListAction, UserRetrieveAction, UserUpdateAction
from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import User, UserInput, UserOutput, UserPartialInput

router = APIRouter()


@router.post("/", name="user:create", status_code=201)
@inject
async def create_user(
    user_input: UserInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: UserCreateAction = Depends(Provide(Container.user_create_action)),
) -> UserOutput:
    db_user = User(**user_input.model_dump())
    await action(db_user)

    output = UserOutput(id=db_user.id, email=db_user.email, username=db_user.username)

    return output


@router.get("/", name="user:list")
@inject
async def list_users(
    pagination: Annotated[dict[str, int | None], Depends(pagination_params)],
    user: Annotated[User, Depends(authenticate_user)],
    action: UserListAction = Depends(Provide(Container.user_list_action)),
) -> list[UserOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    users = await action(limit=limit, offset=offset)

    output = []
    for db_user in users:
        output.append(UserOutput(id=db_user.id, email=db_user.email, username=db_user.username))

    return output


@router.get("/{user_id}", name="user:retrieve")
@inject
async def retrieve_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: UserRetrieveAction = Depends(Provide(Container.user_retrieve_action)),
) -> UserOutput:
    db_user = await action(pk=user_id)
    if not db_user:
        raise HTTPException(status_code=404)

    return UserOutput(id=db_user.id, username=db_user.username, email=db_user.email)


@router.delete("/{user_id}", name="user:delete", status_code=204)
@inject
async def delete_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: UserDeleteAction = Depends(Provide(Container.user_delete_action)),
) -> None:
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    try:
        await action(pk=user_id)
    except NoResultFound:
        raise HTTPException(status_code=404)


@router.patch("/{user_id}", name="user:update")
@inject
async def update_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user_input: UserPartialInput,
    user: Annotated[User, Depends(authenticate_user)],
    update_action: UserUpdateAction = Depends(Provide(Container.user_create_action)),
) -> UserOutput:
    user_data = user_input.model_dump(exclude_unset=True)

    try:
        db_user = await update_action(user_id, user_data)
    except NotFoundException:
        raise HTTPException(status_code=404)

    return UserOutput(id=db_user.id, username=db_user.username, email=db_user.email)
