from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from meldingen.actions.user import (
    UserCreateAction,
    UserDeleteAction,
    UserListAction,
    UserRetrieveAction,
    UserUpdateAction,
)
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import conflict_response, list_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import (
    user_create_action,
    user_delete_action,
    user_list_action,
    user_repository,
    user_retrieve_action,
    user_update_action,
)
from meldingen.models import User
from meldingen.repositories import UserRepository
from meldingen.schemas.input import UserCreateInput, UserUpdateInput
from meldingen.schemas.output import UserOutput

router = APIRouter()


def _hydrate_output(user: User) -> UserOutput:
    return UserOutput(
        id=user.id, email=user.email, username=user.username, created_at=user.created_at, updated_at=user.updated_at
    )


@router.post(
    "/",
    name="user:create",
    status_code=HTTP_201_CREATED,
    responses={**unauthorized_response, **conflict_response},
    dependencies=[Depends(authenticate_user)],
)
async def create_user(
    user_input: UserCreateInput,
    action: Annotated[UserCreateAction, Depends(user_create_action)],
) -> UserOutput:
    db_user = User(**user_input.model_dump())
    await action(db_user)

    return _hydrate_output(db_user)


async def content_range_header_adder(
    repo: Annotated[UserRepository, Depends(user_repository)],
) -> ContentRangeHeaderAdder[User]:
    return ContentRangeHeaderAdder(repo, "user")


@router.get(
    "/",
    name="user:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(authenticate_user)],
)
async def list_users(
    response: Response,
    content_range_header: Annotated[ContentRangeHeaderAdder[User], Depends(content_range_header_adder)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[UserListAction, Depends(user_list_action)],
) -> list[UserOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    users = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )

    await content_range_header(response, pagination)

    return [_hydrate_output(db_user) for db_user in users]


@router.get(
    "/{user_id}",
    name="user:retrieve",
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
async def retrieve_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    action: Annotated[UserRetrieveAction, Depends(user_retrieve_action)],
) -> UserOutput:
    db_user = await action(pk=user_id)
    if not db_user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return _hydrate_output(db_user)


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
async def delete_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: Annotated[UserDeleteAction, Depends(user_delete_action)],
) -> None:
    if user.id == user_id:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    try:
        await action(pk=user_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)


@router.patch(
    "/{user_id}",
    name="user:update",
    responses={**unauthorized_response, **not_found_response, **conflict_response},
    dependencies=[Depends(authenticate_user)],
)
async def update_user(
    user_id: Annotated[int, Path(description="The id of the user.", ge=1)],
    user_input: UserUpdateInput,
    action: Annotated[UserUpdateAction, Depends(user_update_action)],
) -> UserOutput:
    user_data = user_input.model_dump(exclude_unset=True)

    try:
        db_user = await action(user_id, user_data)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return _hydrate_output(db_user)
