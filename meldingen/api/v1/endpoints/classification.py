from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from meldingen_core.actions.classification import ClassificationCreateAction, ClassificationUpdateAction
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from meldingen.actions import ClassificationListAction, ClassificationRetrieveAction
from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Classification, ClassificationInput, ClassificationOutput, User
from meldingen.repositories import ClassificationRepository

router = APIRouter()


@router.post("/", name="classification:create", status_code=HTTP_201_CREATED)
@inject
async def create_classification(
    classification_input: ClassificationInput,
    action: ClassificationCreateAction = Depends(Provide[Container.classification_create_action]),
    user: User = Depends(authenticate_user),
) -> ClassificationOutput:
    db_model = Classification(**classification_input.model_dump())

    await action(db_model)

    return ClassificationOutput(id=db_model.id, name=db_model.name)


@router.get("/", name="classification:list")
@inject
async def list_classifications(
    pagination: dict[str, int | None] = Depends(pagination_params),
    action: ClassificationListAction = Depends(Provide[Container.classification_list_action]),
    user: User = Depends(authenticate_user),
) -> list[ClassificationOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    classifications = await action(limit=limit, offset=offset)

    output = []
    for classification in classifications:
        output.append(ClassificationOutput(id=classification.id, name=classification.name))

    return output


@router.get("/{classification_id}", name="classification:retrieve")
@inject
async def retrieve_classification(
    classification_id: int,
    action: ClassificationRetrieveAction = Depends(Provide[Container.classification_retrieve_action]),
    user: User = Depends(authenticate_user),
) -> ClassificationOutput:
    classification = await action(classification_id)
    if classification is None:
        raise HTTPException(HTTP_404_NOT_FOUND)

    return ClassificationOutput(id=classification.id, name=classification.name)


@router.patch("/{classification_id}", name="classification:update")
@inject
async def update_classification(
    classification_id: int,
    classification_input: ClassificationInput,
    repository: ClassificationRepository = Depends(Provide[Container.classification_repository]),
    action: ClassificationUpdateAction = Depends(Provide[Container.classification_update_action]),
    user: User = Depends(authenticate_user),
) -> ClassificationOutput:
    classification = await repository.retrieve(classification_id)
    if classification is None:
        raise HTTPException(HTTP_404_NOT_FOUND)

    classification_data = classification_input.model_dump(exclude_unset=True)
    for key, value in classification_data.items():
        setattr(classification, key, value)

    await action(classification)

    return ClassificationOutput(id=classification, name=classification.name)
