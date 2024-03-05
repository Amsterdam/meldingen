from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path
from meldingen_core.actions.classification import ClassificationCreateAction, ClassificationDeleteAction
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from meldingen.actions import ClassificationListAction, ClassificationRetrieveAction, ClassificationUpdateAction
from meldingen.api.utils import pagination_params
from meldingen.api.v1 import not_found_response
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Classification, ClassificationInput, ClassificationOutput, User

router = APIRouter()


@router.post("/", name="classification:create", status_code=HTTP_201_CREATED)
@inject
async def create_classification(
    classification_input: ClassificationInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: ClassificationCreateAction = Depends(Provide[Container.classification_create_action]),
) -> ClassificationOutput:
    db_model = Classification(**classification_input.model_dump())

    await action(db_model)

    return ClassificationOutput(id=db_model.id, name=db_model.name)


@router.get("/", name="classification:list")
@inject
async def list_classifications(
    pagination: Annotated[dict[str, int | None], Depends(pagination_params)],
    user: Annotated[User, Depends(authenticate_user)],
    action: ClassificationListAction = Depends(Provide[Container.classification_list_action]),
) -> list[ClassificationOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    classifications = await action(limit=limit, offset=offset)

    output = []
    for classification in classifications:
        output.append(ClassificationOutput(id=classification.id, name=classification.name))

    return output


@router.get("/{classification_id}", name="classification:retrieve", responses={**not_found_response})
@inject
async def retrieve_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: ClassificationRetrieveAction = Depends(Provide[Container.classification_retrieve_action]),
) -> ClassificationOutput:
    classification = await action(classification_id)
    if classification is None:
        raise HTTPException(HTTP_404_NOT_FOUND)

    return ClassificationOutput(id=classification.id, name=classification.name)


@router.patch("/{classification_id}", name="classification:update", responses={**not_found_response})
@inject
async def update_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    classification_input: ClassificationInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: ClassificationUpdateAction = Depends(Provide[Container.classification_update_action]),
) -> ClassificationOutput:
    classification_data = classification_input.model_dump(exclude_unset=True)

    try:
        classification = await action(classification_id, classification_data)
    except NotFoundException:
        raise HTTPException(HTTP_404_NOT_FOUND)

    return ClassificationOutput(id=classification.id, name=classification.name)


@router.delete(
    "/{classification_id}",
    name="classification:delete",
    status_code=HTTP_204_NO_CONTENT,
    responses={
        **not_found_response,
        "default": {"description": "Unexpected error"},
    },
)
@inject
async def delete_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: ClassificationDeleteAction = Depends(Provide[Container.classification_delete_action]),
) -> None:
    try:
        await action(classification_id)
    except NotFoundException:
        raise HTTPException(HTTP_404_NOT_FOUND)
