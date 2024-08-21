from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Response
from meldingen_core.exceptions import NotFoundException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from meldingen.actions import (
    FormCreateAction,
    FormDeleteAction,
    FormListAction,
    FormRetrieveAction,
    FormRetrieveByClassificationAction,
    FormUpdateAction,
)
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import list_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.dependencies import (
    form_create_action,
    form_delete_action,
    form_list_action,
    form_output_factory,
    form_repository,
    form_retrieve_action,
    form_retrieve_by_classification_action,
)
from meldingen.models import User
from meldingen.output_schemas import FormOutput, SimpleFormOutput
from meldingen.repositories import FormRepository
from meldingen.schema_factories import FormOutputFactory
from meldingen.schemas import FormInput

router = APIRouter()


async def _add_content_range_header(
    response: Response,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    repository: Annotated[FormRepository, Depends(form_repository)],
) -> None:
    await ContentRangeHeaderAdder(repository, "form")(response, pagination)


@router.get(
    "/",
    name="form:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(_add_content_range_header), Depends(authenticate_user)],
)
async def list_form(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[FormListAction, Depends(form_list_action)],
) -> list[SimpleFormOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    forms = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )

    output = []
    for db_form in forms:
        output.append(
            SimpleFormOutput(
                id=db_form.id,
                title=db_form.title,
                display=db_form.display,
                classification=db_form.classification_id,
                created_at=db_form.created_at,
                updated_at=db_form.updated_at,
            )
        )

    return output


@router.get("/{form_id}", name="form:retrieve", responses={**not_found_response})
async def retrieve_form(
    form_id: Annotated[int, Path(description="The id of the form.", ge=1)],
    action: Annotated[FormRetrieveAction, Depends(form_retrieve_action)],
    produce_output_model: Annotated[FormOutputFactory, Depends(form_output_factory)],
) -> FormOutput:
    db_form = await action(pk=form_id)
    if not db_form:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await produce_output_model(db_form)


@router.get("/classification/{classification_id}", name="form:classification", responses={**not_found_response})
async def retrieve_form_by_classification(
    classification_id: Annotated[int, Path(description="The id of the classification that the form belongs to.", ge=1)],
    action: Annotated[FormRetrieveByClassificationAction, Depends(form_retrieve_by_classification_action)],
    produce_output_model: Annotated[FormOutputFactory, Depends(form_output_factory)],
) -> FormOutput:
    form = await action(classification_id)

    return await produce_output_model(form)


@router.post(
    "/",
    name="form:create",
    status_code=HTTP_201_CREATED,
    responses={
        **unauthorized_response,
        HTTP_400_BAD_REQUEST: {
            "description": "Providing a classification id that does not exist",
            "content": {"application/json": {"example": {"detail": "Classification not found"}}},
        },
    },
    dependencies=[Depends(authenticate_user)],
)
async def create_form(
    form_input: FormInput,
    action: Annotated[FormCreateAction, Depends(form_create_action)],
    produce_output_model: Annotated[FormOutputFactory, Depends(form_output_factory)],
) -> FormOutput:
    form = await action(form_input)

    return await produce_output_model(form)


@router.put(
    "/{form_id}",
    name="form:update",
    responses={
        **unauthorized_response,
        **not_found_response,
        HTTP_400_BAD_REQUEST: {
            "description": "Providing a classification id that does not exist",
            "content": {"application/json": {"example": {"detail": "Classification not found"}}},
        },
    },
)
@inject
async def update_form(
    form_id: Annotated[int, Path(description="The id of the form.", ge=1)],
    form_input: FormInput,
    user: Annotated[User, Depends(authenticate_user)],
    action: FormUpdateAction = Depends(Provide(Container.form_update_action)),
    produce_output_model: FormOutputFactory = Depends(Provide[Container.form_output_factory]),
) -> FormOutput:
    db_form = await action(form_id, form_input)

    return await produce_output_model(form=db_form)


@router.delete(
    "/{form_id}",
    name="form:delete",
    status_code=HTTP_204_NO_CONTENT,
    responses={
        **unauthorized_response,
        **not_found_response,
    },
    dependencies=[Depends(authenticate_user)],
)
async def delete_form(
    form_id: Annotated[int, Path(description="The id of the form.", ge=1)],
    action: Annotated[FormDeleteAction, Depends(form_delete_action)],
) -> None:
    try:
        await action(pk=form_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
