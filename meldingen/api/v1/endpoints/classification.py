from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends
from meldingen.containers import Container
from meldingen_core.actions.classification import ClassificationCreateAction

from meldingen.authentication import authenticate_user
from meldingen.models import Classification, ClassificationInput, ClassificationOutput, User

router = APIRouter()


@router.get("/", name="classification:create", status_code=201)
@inject
async def create_classification(
    classification_input: ClassificationInput,
    action: ClassificationCreateAction = Depends(Provide[Container.classification_create_action]),
    user: User = Depends(authenticate_user),
) -> ClassificationOutput:
    db_model = Classification(**classification_input.model_dump())

    await action(db_model)

    return ClassificationOutput(id=db_model.id, name=db_model.name)
