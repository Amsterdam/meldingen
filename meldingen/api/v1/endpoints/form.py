# from typing import Annotated
#
# from dependency_injector.wiring import Provide, inject
# from fastapi import APIRouter, Depends, HTTPException, Path, Response
# from meldingen_core.exceptions import NotFoundException
# from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
#
# from meldingen.actions import (
#     FormCreateAction,
#     FormDeleteAction,
#     FormListAction,
#     FormRetrieveAction,
#     FormRetrieveByClassificationAction,
#     FormUpdateAction,
# )
# from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
# from meldingen.api.v1 import list_response, not_found_response, unauthorized_response
# from meldingen.authentication import authenticate_user
# from meldingen.containers import Container
# from meldingen.models import User
# from meldingen.repositories import FormRepository
# from meldingen.schema_renderer import FormOutPutRenderer
# from meldingen.schemas import FormInput, FormOnlyOutput, FormOutput
#
# router = APIRouter()
#
#
# _hydrate_output = FormOutPutRenderer()
#
#
# @inject
# async def _add_content_range_header(
#     response: Response,
#     pagination: Annotated[PaginationParams, Depends(pagination_params)],
#     repo: FormRepository = Depends(Provide[Container.form_repository]),
# ) -> None:
#     await ContentRangeHeaderAdder(repo, "form")(response, pagination)
#
#
# @router.get(
#     "/",
#     name="form:list",
#     responses={**list_response, **unauthorized_response},
#     dependencies=[Depends(_add_content_range_header)],
# )
# @inject
# async def list_form(
#     pagination: Annotated[PaginationParams, Depends(pagination_params)],
#     sort: Annotated[SortParams, Depends(sort_param)],
#     user: Annotated[User, Depends(authenticate_user)],
#     action: FormListAction = Depends(Provide(Container.form_list_action)),
# ) -> list[FormOnlyOutput]:
#     limit = pagination["limit"] or 0
#     offset = pagination["offset"] or 0
#
#     forms = await action(
#         limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
#     )
#
#     output = []
#     for db_form in forms:
#         output.append(
#             FormOnlyOutput(
#                 id=db_form.id,
#                 title=db_form.title,
#                 display=db_form.display,
#                 classification=db_form.classification_id,
#                 created_at=db_form.created_at,
#                 updated_at=db_form.updated_at,
#             )
#         )
#
#     return output
#
#
# @router.get("/{form_id}", name="form:retrieve", responses={**not_found_response})
# @inject
# async def retrieve_form(
#     form_id: Annotated[int, Path(description="The id of the form.", ge=1)],
#     action: FormRetrieveAction = Depends(Provide(Container.form_retrieve_action)),
# ) -> FormOutput:
#     db_form = await action(pk=form_id)
#     if not db_form:
#         raise HTTPException(status_code=HTTP_404_NOT_FOUND)
#
#     return await _hydrate_output(db_form)
#
#
# @router.get("/classification/{classification_id}", name="form:classification", responses={**not_found_response})
# @inject
# async def retrieve_form_by_classification(
#     classification_id: Annotated[int, Path(description="The id of the classification that the form belongs to.", ge=1)],
#     action: FormRetrieveByClassificationAction = Depends(Provide(Container.form_classification_action)),
# ) -> FormOutput:
#     form = await action(classification_id)
#
#     return await _hydrate_output(form)
#
#
# @router.post(
#     "/",
#     name="form:create",
#     status_code=HTTP_201_CREATED,
#     responses={
#         **unauthorized_response,
#         HTTP_400_BAD_REQUEST: {
#             "description": "Providing a classification id that does not exist",
#             "content": {"application/json": {"example": {"detail": "Classification not found"}}},
#         },
#     },
# )
# @inject
# async def create_form(
#     form_input: FormInput,
#     user: Annotated[User, Depends(authenticate_user)],
#     action: FormCreateAction = Depends(Provide(Container.form_create_action)),
# ) -> FormOutput:
#     form = await action(form_input)
#
#     return await _hydrate_output(form)
#
#
# @router.put(
#     "/{form_id}",
#     name="form:update",
#     responses={
#         **unauthorized_response,
#         **not_found_response,
#         HTTP_400_BAD_REQUEST: {
#             "description": "Providing a classification id that does not exist",
#             "content": {"application/json": {"example": {"detail": "Classification not found"}}},
#         },
#     },
# )
# @inject
# async def update_form(
#     form_id: Annotated[int, Path(description="The id of the form.", ge=1)],
#     form_input: FormInput,
#     user: Annotated[User, Depends(authenticate_user)],
#     action: FormUpdateAction = Depends(Provide(Container.form_update_action)),
# ) -> FormOutput:
#     db_form = await action(form_id, form_input)
#
#     return await _hydrate_output(form=db_form)
#
#
# @router.delete(
#     "/{form_id}",
#     name="form:delete",
#     status_code=HTTP_204_NO_CONTENT,
#     responses={
#         **unauthorized_response,
#         **not_found_response,
#     },
# )
# @inject
# async def delete_form(
#     form_id: Annotated[int, Path(description="The id of the form.", ge=1)],
#     user: Annotated[User, Depends(authenticate_user)],
#     action: FormDeleteAction = Depends(Provide(Container.form_delete_action)),
# ) -> None:
#     try:
#         await action(pk=form_id)
#     except NotFoundException:
#         raise HTTPException(status_code=HTTP_404_NOT_FOUND)
