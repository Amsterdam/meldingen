from typing import Annotated, Literal, overload

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_CONTENT

from meldingen.actions.classification import (
    ClassificationCreateAction,
    ClassificationDeleteAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
    DefaultClassificationCannotBeDeleted,
    DefaultClassificationNameCannotBeUpdated,
)
from meldingen.api.utils import (
    ContentRangeHeaderAdder,
    PaginationParams,
    SortParams,
    pagination_params,
    sort_param,
)
from meldingen.api.v1 import conflict_response, list_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user, is_authenticated_request
from meldingen.dependencies import (
    classification_create_action,
    classification_delete_action,
    classification_list_action,
    classification_repository,
    classification_retrieve_action,
    classification_update_action,
    list_filters,
)
from meldingen.models import Classification
from meldingen.repositories import ClassificationRepository, RepositoryListFilters
from meldingen.schemas.input import ClassificationCreateInput, ClassificationUpdateInput
from meldingen.schemas.output import ClassificationOutput, ClassificationOutputPublic

router = APIRouter()


async def content_range_header_adder(
    repo: Annotated[ClassificationRepository, Depends(classification_repository)],
) -> ContentRangeHeaderAdder[Classification]:
    return ContentRangeHeaderAdder(repo, "classification")


@overload
async def _hydrate_output(classification: Classification, public: bool) -> ClassificationOutputPublic: ...


@overload
async def _hydrate_output(classification: Classification, public: Literal[False] = False) -> ClassificationOutput: ...


async def _hydrate_output(
    classification: Classification, public: bool = False
) -> ClassificationOutput | ClassificationOutputPublic:
    form_id = None

    form = await classification.awaitable_attrs.form
    if form is not None:
        form_id = form.id

    if public:
        return ClassificationOutputPublic(
            id=classification.id,
            name=classification.name,
            service_level_objective_text=classification.service_level_objective_text,
            service_level_objective_days=classification.service_level_objective_days,
            service_level_objective_day_type=classification.service_level_objective_day_type,
            created_at=classification.created_at,
            updated_at=classification.updated_at,
        )

    return ClassificationOutput(
        id=classification.id,
        form=form_id,
        name=classification.name,
        instructions=classification.instructions,
        asset_type=classification.asset_type_id,
        created_at=classification.created_at,
        updated_at=classification.updated_at,
        service_level_objective_text=classification.service_level_objective_text,
        service_level_objective_days=classification.service_level_objective_days,
        service_level_objective_day_type=classification.service_level_objective_day_type,
    )


@router.post(
    "/",
    name="classification:create",
    status_code=HTTP_201_CREATED,
    responses={**unauthorized_response, **conflict_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
async def create_classification(
    classification_input: ClassificationCreateInput,
    action: Annotated[ClassificationCreateAction, Depends(classification_create_action)],
) -> ClassificationOutput:
    values = classification_input.model_dump()
    asset_type_id = values.pop("asset_type")
    classification = Classification(**values)

    try:
        await action(classification, asset_type_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Asset type not found")

    return await _hydrate_output(classification)


@router.get(
    "/",
    name="classification:list",
    responses={**list_response},
    description="""
    Retrieve a list of classifications with optional filtering, sorting, and pagination.
    If the request is unauthenticated, only public fields (See `ClassificationOutputPublic` schema) will be included in the response.
    """,
)
async def list_classifications(
    response: Response,
    content_range_header_adder: Annotated[ContentRangeHeaderAdder[Classification], Depends(content_range_header_adder)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    is_authenticated_request: Annotated[bool, Depends(is_authenticated_request)],
    action: Annotated[ClassificationListAction, Depends(classification_list_action)],
    list_filters: Annotated[RepositoryListFilters | None, Depends(list_filters)],
    include_deleted: Annotated[
        bool,
        Query(
            description="Include soft-deleted classifications in the list result when true.",
        ),
    ] = False,
) -> list[ClassificationOutput] | list[ClassificationOutputPublic]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    classifications = await action(
        limit=limit,
        offset=offset,
        sort_attribute_name=sort.get_attribute_name(),
        sort_direction=sort.get_direction(),
        filters=list_filters,
        apply_visibility_filters=not include_deleted,
    )
    await content_range_header_adder(
        response,
        pagination,
        list_filters,
        apply_visibility_filters=not include_deleted,
    )

    return [
        await _hydrate_output(classification, public=not is_authenticated_request) for classification in classifications
    ]


@router.get(
    "/{classification_id}",
    name="classification:retrieve",
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
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
async def update_classification(
    classification_id: Annotated[int, Path(description="The classification id.", ge=1)],
    classification_input: ClassificationUpdateInput,
    action: Annotated[ClassificationUpdateAction, Depends(classification_update_action)],
) -> ClassificationOutput:
    classification_data = classification_input.model_dump(exclude_unset=True)

    try:
        classification = await action(classification_id, classification_data)
    except NotFoundException:
        raise HTTPException(HTTP_404_NOT_FOUND)
    except DefaultClassificationNameCannotBeUpdated:
        raise HTTPException(HTTP_422_UNPROCESSABLE_CONTENT, detail="Default classification name cannot be updated.")

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
    except DefaultClassificationCannotBeDeleted:
        raise HTTPException(HTTP_422_UNPROCESSABLE_CONTENT, detail="Default classification cannot be deleted.")
