from typing import Annotated

from fastapi import Depends, HTTPException, Path
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions.classification import (
    ClassificationRetrieveAction,
)
from meldingen.api.utils import create_router
from meldingen.dependencies import (
    classification_retrieve_action,
)
from meldingen.models import Classification
from meldingen.schemas.output import ClassificationOutputPublic

router = create_router()


async def _hydrate_output(classification: Classification) -> ClassificationOutputPublic:
    return ClassificationOutputPublic(
        id=classification.id,
        name=classification.name,
        created_at=classification.created_at,
        updated_at=classification.updated_at,
        service_level_objective_text=classification.service_level_objective_text,
        service_level_objective_days=classification.service_level_objective_days,
        service_level_objective_day_type=classification.service_level_objective_day_type,
    )


@router.get(
    "/{classification_id}",
    name="public:classification:retrieve",
)
async def retrieve_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    action: Annotated[ClassificationRetrieveAction, Depends(classification_retrieve_action)],
) -> ClassificationOutputPublic:
    classification = await action(classification_id)
    if not classification:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Classification not found")

    return await _hydrate_output(classification)
