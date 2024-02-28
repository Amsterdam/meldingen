from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from meldingen_core.actions.classification import ClassificationCreateAction

from meldingen.actions import ClassificationListAction
from meldingen.api.utils import pagination_params
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Classification, ClassificationInput, ClassificationOutput, User

router = APIRouter()


@router.post("/", name="classification:create", status_code=201)
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
