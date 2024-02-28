from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from meldingen_core.actions.user import UserCreateAction, UserDeleteAction, UserUpdateAction
from sqlalchemy.exc import NoResultFound

from meldingen.actions import UserListAction, UserRetrieveAction
from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import User, UserInput, UserOutput, UserPartialInput

router = APIRouter()


@router.post("/", name="user:create", status_code=201)
@inject
async def create_user(
    user_input: UserInput,
    action: UserCreateAction = Depends(Provide(Container.user_create_action)),
    user: User = Depends(authenticate_user),
) -> UserOutput:
    db_user = User(**user_input.model_dump())
    await action(db_user)

    output = UserOutput(id=db_user.id, email=db_user.email, username=db_user.username)

    return output


@router.get("/", name="user:list")
@inject
async def list_users(
    pagination: dict[str, int | None] = Depends(pagination_params),
    action: UserListAction = Depends(Provide(Container.user_list_action)),
    user: User = Depends(authenticate_user),
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
    user_id: int,
    action: UserRetrieveAction = Depends(Provide(Container.user_retrieve_action)),
    user: User = Depends(authenticate_user),
) -> UserOutput:
    db_user = await action(pk=user_id)
    if not db_user:
        raise HTTPException(status_code=404)

    return UserOutput(id=db_user.id, username=db_user.username, email=db_user.email)


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


@router.patch("/{user_id}", name="user:update")
@inject
async def update_user(
    user_id: int,
    user_input: UserPartialInput,
    retrieve_action: UserRetrieveAction = Depends(Provide(Container.user_retrieve_action)),
    update_action: UserUpdateAction = Depends(Provide(Container.user_create_action)),
    user: User = Depends(authenticate_user),
) -> UserOutput:
    db_user = await retrieve_action(pk=user_id)
    if not db_user:
        raise HTTPException(status_code=404)

    user_data = user_input.model_dump(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)

    await update_action(db_user)

    return UserOutput(id=db_user.id, username=db_user.username, email=db_user.email)
