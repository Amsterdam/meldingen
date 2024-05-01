from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Response
from meldingen_core.actions.user import UserCreateAction, UserDeleteAction
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from meldingen.actions import UserListAction, UserRetrieveAction, UserUpdateAction
from meldingen.api.utils import PaginationParams, pagination_params
from meldingen.api.v1 import conflict_response, list_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import User
from meldingen.repositories import UserRepository
from meldingen.schemas import UserCreateInput, UserOutput, UserUpdateInput

router = APIRouter()


@router.post(
    "/", name="user:create", status_code=HTTP_201_CREATED, responses={**unauthorized_response, **conflict_response}
)
@inject
async def create_user(
    user_input: UserCreateInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: UserCreateAction = Depends(Provide(Container.user_create_action)),
) -> UserOutput:
    db_user = User(**user_input.model_dump())
    await action(db_user)

    output = UserOutput(id=db_user.id, email=db_user.email, username=db_user.username)

    return output


@router.get("/", name="user:list", responses={**list_response, **unauthorized_response})
@inject
async def list_users(
    response: Response,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    user: Annotated[User, Depends(authenticate_user)],
    action: UserListAction = Depends(Provide(Container.user_list_action)),
    repository: UserRepository = Depends(Provide(Container.user_repository)),
) -> list[UserOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    users = await action(limit=limit, offset=offset)

    output = []
    for db_user in users:
        output.append(UserOutput(id=db_user.id, email=db_user.email, username=db_user.username))

    response.headers["Content-Range"] = f"user {offset}-{limit - 1 + offset}/{await repository.count()}"

    return output


@router.get("/{user_id}", name="user:retrieve", responses={**unauthorized_response, **not_found_response})
@inject
async def retrieve_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: UserRetrieveAction = Depends(Provide(Container.user_retrieve_action)),
) -> UserOutput:
    db_user = await action(pk=user_id)
    if not db_user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return UserOutput(id=db_user.id, username=db_user.username, email=db_user.email)


@router.delete(
    "/{user_id}",
    name="user:delete",
    status_code=HTTP_204_NO_CONTENT,
    responses={
        HTTP_400_BAD_REQUEST: {
            "description": "Delete own account",
            "content": {"application/json": {"example": {"detail": "You cannot delete your own account"}}},
        },
        **unauthorized_response,
        **not_found_response,
    },
)
@inject
async def delete_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: UserDeleteAction = Depends(Provide(Container.user_delete_action)),
) -> None:
    if user.id == user_id:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    try:
        await action(pk=user_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)


@router.patch(
    "/{user_id}", name="user:update", responses={**unauthorized_response, **not_found_response, **conflict_response}
)
@inject
async def update_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user_input: UserUpdateInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: UserUpdateAction = Depends(Provide(Container.user_update_action)),
) -> UserOutput:
    user_data = user_input.model_dump(exclude_unset=True)

    try:
        db_user = await action(user_id, user_data)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return UserOutput(id=db_user.id, username=db_user.username, email=db_user.email)
