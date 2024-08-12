from typing import Annotated

import structlog
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, UploadFile
from meldingen_core.actions.melding import (
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingCreateAction,
    MeldingProcessAction,
    MeldingUpdateAction,
)
from meldingen_core.classification import ClassificationNotFoundException
from meldingen_core.exceptions import NotFoundException
from meldingen_core.token import TokenException
from mp_fsm.statemachine import WrongStateException
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from meldingen.actions import AnswerCreateAction, MeldingListAction, MeldingRetrieveAction, UploadAttachmentAction
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import (
    default_response,
    list_response,
    not_found_response,
    transition_not_allowed,
    unauthorized_response,
)
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.dependencies import (
    melding_create_action,
    melding_list_action,
    melding_retrieve_action,
    melding_update_action,
)
from meldingen.exceptions import MeldingNotClassifiedException
from meldingen.models import Melding, User
from meldingen.repositories import MeldingRepository
from meldingen.schemas import (
    AnswerInput,
    AnswerOutput,
    AttachmentOutput,
    MeldingCreateOutput,
    MeldingInput,
    MeldingOutput,
)

router = APIRouter()
logger = structlog.get_logger()


def _hydrate_output(melding: Melding) -> MeldingOutput:
    return MeldingOutput(
        id=melding.id,
        text=melding.text,
        state=melding.state,
        classification=melding.classification_id,
        created_at=melding.created_at,
        updated_at=melding.updated_at,
    )


@router.post("/", name="melding:create", status_code=HTTP_201_CREATED)
@inject
async def create_melding(
    melding_input: MeldingInput,
    action: Annotated[MeldingCreateAction[Melding, Melding], Depends(melding_create_action)],
) -> MeldingCreateOutput:
    melding = Melding(**melding_input.model_dump())

    await action(melding)

    return MeldingCreateOutput(
        id=melding.id,
        text=melding.text,
        state=melding.state,
        classification=melding.classification_id,
        token=melding.token,
        created_at=melding.created_at,
        updated_at=melding.updated_at,
    )


@inject
async def _add_content_range_header(
    response: Response,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    repo: MeldingRepository = Depends(Provide[Container.melding_repository]),
) -> None:
    await ContentRangeHeaderAdder(repo, "melding")(response, pagination)


@router.get(
    "/",
    name="melding:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(_add_content_range_header), Depends(authenticate_user)],
)
@inject
async def list_meldingen(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[MeldingListAction, Depends(melding_list_action)],
) -> list[MeldingOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    meldingen = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )
    output = []
    for melding in meldingen:
        output.append(_hydrate_output(melding))

    return output


@router.get(
    "/{melding_id}",
    name="melding:retrieve",
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
@inject
async def retrieve_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[MeldingRetrieveAction, Depends(melding_retrieve_action)],
) -> MeldingOutput:
    melding = await action(pk=melding_id)

    if not melding:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return _hydrate_output(melding)


@router.patch(
    "/{melding_id}",
    name="melding:update",
    status_code=HTTP_200_OK,
    responses={**unauthorized_response, **not_found_response},
)
@inject
async def update_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    melding_input: MeldingInput,
    action: Annotated[MeldingUpdateAction[Melding, Melding], Depends(melding_update_action)],
) -> MeldingOutput:
    try:
        melding = await action(pk=melding_id, values=melding_input.model_dump(), token=token)
    except ClassificationNotFoundException:
        logger.error("Classifier failed to find classification!")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return _hydrate_output(melding)


@router.put(
    "/{melding_id}/answer_questions",
    name="melding:answer_questions",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
)
@inject
async def answer_questions(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: MeldingAnswerQuestionsAction[Melding, Melding] = Depends(
        Provide(Container.melding_answer_questions_action)
    ),
) -> MeldingOutput:
    try:
        melding = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return _hydrate_output(melding)


@router.put(
    "/{melding_id}/process",
    name="melding:process",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
)
@inject
async def process_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: MeldingProcessAction[Melding, Melding] = Depends(Provide(Container.melding_process_action)),
) -> MeldingOutput:
    try:
        melding = await action(melding_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")

    return _hydrate_output(melding)


@router.put(
    "/{melding_id}/complete",
    name="melding:complete",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
)
@inject
async def complete_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: MeldingCompleteAction[Melding, Melding] = Depends(Provide(Container.melding_complete_action)),
) -> MeldingOutput:
    try:
        melding = await action(melding_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")

    return _hydrate_output(melding)


@router.post(
    "/{melding_id}/question/{question_id}",
    name="melding:answer-question",
    status_code=HTTP_201_CREATED,
    responses={
        **not_found_response,
        **unauthorized_response,
        **default_response,
        **{
            HTTP_400_BAD_REQUEST: {
                "description": "",
                "content": {
                    "application/json": {
                        "examples": {
                            "The melding is not classified.": {"value": {"detail": "Melding not classified"}},
                            "The melding and form classifications are not the same ": {
                                "value": {"detail": "Classification mismatch"}
                            },
                        }
                    }
                },
            }
        },
    },
)
@inject
async def answer_additional_question(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    question_id: Annotated[int, Path(description="The id of the question.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    answer_input: AnswerInput,
    action: AnswerCreateAction = Depends(Provide(Container.answer_create_action)),
) -> AnswerOutput:
    try:
        answer = await action(melding_id, token, question_id, answer_input)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
    except MeldingNotClassifiedException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Melding not classified")

    return AnswerOutput(id=answer.id, created_at=answer.created_at, updated_at=answer.updated_at)


@router.post(
    "/{melding_id}/attachment",
    name="melding:attachment",
    responses={
        **not_found_response,
        **unauthorized_response,
    },
)
@inject
async def upload_attachment(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    file: UploadFile,
    action: UploadAttachmentAction = Depends(Provide(Container.upload_attachment_action)),
) -> AttachmentOutput:
    # When uploading a file without filename, Starlette gives us a string instead of an instance of UploadFile,
    # so actually the filename will always be available. To satisfy the type checker we assert that is the case.
    assert file.filename is not None

    try:
        attachment = await action(melding_id, token, file.filename, await file.read())
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return AttachmentOutput(
        id=attachment.id,
        original_filename=attachment.original_filename,
        created_at=attachment.created_at,
        updated_at=attachment.updated_at,
    )
