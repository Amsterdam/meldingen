from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Response
from meldingen_core.actions.classification import ClassificationCreateAction
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from meldingen.actions import (
    ClassificationDeleteAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
)
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import conflict_response, list_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.dependencies import (
    classification_delete_action,
    classification_list_action,
    classification_retrieve_action,
    classification_update_action,
)
from meldingen.models import Classification
from meldingen.repositories import ClassificationRepository
from meldingen.schemas import ClassificationInput, ClassificationOutput

router = APIRouter()


@router.post(
    "/",
    name="classification:create",
    status_code=HTTP_201_CREATED,
    responses={**unauthorized_response, **conflict_response},
    dependencies=[Depends(authenticate_user)],
)
@inject
async def create_classification(
    classification_input: ClassificationInput,
    action: ClassificationCreateAction = Depends(Provide[Container.classification_create_action]),
) -> ClassificationOutput:
    db_model = Classification(**classification_input.model_dump())

    await action(db_model)

    return ClassificationOutput(
        id=db_model.id, name=db_model.name, created_at=db_model.created_at, updated_at=db_model.updated_at
    )


@inject
async def _add_content_range_header(
    response: Response,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    repo: ClassificationRepository = Depends(Provide[Container.classification_repository]),
) -> None:
    await ContentRangeHeaderAdder(repo, "classification")(response, pagination)


async def _hydrate_output(classification: Classification) -> ClassificationOutput:
    form_id = None

    form = await classification.awaitable_attrs.form
    if form is not None:
        form_id = form.id

    return ClassificationOutput(
        id=classification.id,
        form=form_id,
        name=classification.name,
        created_at=classification.created_at,
        updated_at=classification.updated_at,
    )


@router.get(
    "/",
    name="classification:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(_add_content_range_header), Depends(authenticate_user)],
)
@inject
async def list_classifications(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[ClassificationListAction, Depends(classification_list_action)],
) -> list[ClassificationOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    classifications = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )

    output = []
    for classification in classifications:
        output.append(await _hydrate_output(classification))

    return output


@router.get(
    "/{classification_id}",
    name="classification:retrieve",
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
@inject
async def retrieve_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    action: Annotated[ClassificationRetrieveAction, Depends(classification_retrieve_action)],
) -> ClassificationOutput:
    classification = await action(classification_id)
    if classification is None:
        raise HTTPException(HTTP_404_NOT_FOUND)

    return await _hydrate_output(classification)


@router.patch(
    "/{classification_id}",
    name="classification:update",
    responses={**unauthorized_response, **not_found_response, **conflict_response},
    dependencies=[Depends(authenticate_user)],
)
@inject
async def update_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    classification_input: ClassificationInput,
    action: Annotated[ClassificationUpdateAction, Depends(classification_update_action)],
) -> ClassificationOutput:
    classification_data = classification_input.model_dump(exclude_unset=True)

    try:
        classification = await action(classification_id, classification_data)
    except NotFoundException:
        raise HTTPException(HTTP_404_NOT_FOUND)

    return await _hydrate_output(classification)


@router.delete(
    "/{classification_id}",
    name="classification:delete",
    status_code=HTTP_204_NO_CONTENT,
    responses={
        **unauthorized_response,
        **not_found_response,
    },
    dependencies=[Depends(authenticate_user)],
)
async def delete_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    action: Annotated[ClassificationDeleteAction, Depends(classification_delete_action)],
) -> None:
    try:
        await action(classification_id)
    except NotFoundException:
        raise HTTPException(HTTP_404_NOT_FOUND)
