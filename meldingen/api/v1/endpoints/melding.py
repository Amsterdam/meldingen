from typing import Annotated, AsyncIterator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from meldingen_core.actions.attachment import AttachmentTypes
from meldingen_core.actions.melding import (
    MeldingAddAttachmentsAction,
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingCreateAction,
    MeldingProcessAction,
    MeldingSubmitLocationAction,
    MeldingUpdateAction,
)
from meldingen_core.classification import ClassificationNotFoundException
from meldingen_core.exceptions import NotFoundException
from meldingen_core.token import TokenException
from meldingen_core.validators import MediaTypeIntegrityError, MediaTypeNotAllowed
from mp_fsm.statemachine import GuardException, WrongStateException
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from meldingen.actions import (
    AddLocationToMeldingAction,
    AnswerCreateAction,
    DeleteAttachmentAction,
    DownloadAttachmentAction,
    ListAttachmentsAction,
    MeldingListAction,
    MeldingRetrieveAction,
    UploadAttachmentAction,
)
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import (
    default_response,
    list_response,
    not_found_response,
    transition_not_allowed,
    unauthorized_response,
)
from meldingen.authentication import authenticate_user
from meldingen.dependencies import (
    melding_add_attachments_action,
    melding_add_location_action,
    melding_answer_create_action,
    melding_answer_questions_action,
    melding_complete_action,
    melding_create_action,
    melding_delete_attachment_action,
    melding_download_attachment_action,
    melding_list_action,
    melding_list_attachments_action,
    melding_output_factory,
    melding_process_action,
    melding_repository,
    melding_retrieve_action,
    melding_submit_location_action,
    melding_update_action,
    melding_upload_attachment_action,
)
from meldingen.exceptions import MeldingNotClassifiedException
from meldingen.models import Attachment, Melding
from meldingen.repositories import MeldingRepository
from meldingen.schema_factories import MeldingOutputFactory
from meldingen.schemas import (
    AnswerInput,
    AnswerOutput,
    AttachmentOutput,
    GeoJson,
    MeldingCreateOutput,
    MeldingInput,
    MeldingOutput,
)

router = APIRouter()
logger = structlog.get_logger()


# TODO overal vervangen met Melding Responder?
def _hydrate_output(
    melding: Melding,
) -> MeldingOutput:
    return MeldingOutput(
        id=melding.id,
        text=melding.text,
        state=melding.state,
        classification=melding.classification_id,
        created_at=melding.created_at,
        updated_at=melding.updated_at,
    )


@router.post("/", name="melding:create", status_code=HTTP_201_CREATED)
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


async def _add_content_range_header(
    response: Response,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    repo: Annotated[MeldingRepository, Depends(melding_repository)],
) -> None:
    await ContentRangeHeaderAdder(repo, "melding")(response, pagination)


@router.get(
    "/",
    name="melding:list",
    responses={**list_response, **unauthorized_response},
    dependencies=[Depends(_add_content_range_header), Depends(authenticate_user)],
)
async def list_meldingen(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    sort: Annotated[SortParams, Depends(sort_param)],
    action: Annotated[MeldingListAction, Depends(melding_list_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> list[MeldingOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    meldingen = await action(
        limit=limit, offset=offset, sort_attribute_name=sort.get_attribute_name(), sort_direction=sort.get_direction()
    )
    output = []
    for melding in meldingen:
        output.append(produce_output(melding))

    return output


@router.get(
    "/{melding_id}",
    name="melding:retrieve",
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
async def retrieve_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[MeldingRetrieveAction, Depends(melding_retrieve_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    melding = await action(pk=melding_id)

    if not melding:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return produce_output(melding)


@router.patch(
    "/{melding_id}",
    name="melding:update",
    status_code=HTTP_200_OK,
    responses={**unauthorized_response, **not_found_response},
)
async def update_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    melding_input: MeldingInput,
    action: Annotated[MeldingUpdateAction[Melding, Melding], Depends(melding_update_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
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

    return produce_output(melding)


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
async def answer_questions(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MeldingAnswerQuestionsAction[Melding, Melding], Depends(melding_answer_questions_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return produce_output(melding)


@router.put(
    "/{melding_id}/add_attachments",
    name="melding:add-attachments",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
)
async def add_attachments(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MeldingAddAttachmentsAction[Melding, Melding], Depends(melding_add_attachments_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return produce_output(melding)


@router.put(
    "/{melding_id}/submit_location",
    name="melding:submit-location",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
)
async def submit_location(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MeldingSubmitLocationAction[Melding, Melding], Depends(melding_submit_location_action)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")
    except GuardException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Location must be added before submitting")
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
    dependencies=[Depends(authenticate_user)],
)
async def process_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[MeldingProcessAction[Melding, Melding], Depends(melding_process_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")

    return produce_output(melding)


@router.put(
    "/{melding_id}/complete",
    name="melding:complete",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
    dependencies=[Depends(authenticate_user)],
)
async def complete_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[MeldingCompleteAction[Melding, Melding], Depends(melding_complete_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")

    return produce_output(melding)


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
async def answer_additional_question(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    question_id: Annotated[int, Path(description="The id of the question.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    answer_input: AnswerInput,
    action: Annotated[AnswerCreateAction, Depends(melding_answer_create_action)],
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


def _hydrate_attachment_output(attachment: Attachment) -> AttachmentOutput:
    return AttachmentOutput(
        id=attachment.id,
        original_filename=attachment.original_filename,
        created_at=attachment.created_at,
        updated_at=attachment.updated_at,
    )


@router.post(
    "/{melding_id}/attachment",
    name="melding:attachment",
    responses={
        **not_found_response,
        **unauthorized_response,
        **{
            HTTP_400_BAD_REQUEST: {
                "description": "",
                "content": {
                    "application/json": {
                        "examples": {
                            "Uploading attachment with media type that is not allowed.": {
                                "value": {"detail": "Attachment not allowed"}
                            },
                            "Media type of data does not match the media type in the Content-Type header": {
                                "value": {"detail": "Media type of data does not match provided media type"}
                            },
                        },
                    },
                },
            },
            HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
                "description": "Uploading attachment that is too large.",
                "content": {"application/json": {"example": {"detail": "Allowed content size exceeded"}}},
            },
        },
    },
)
async def upload_attachment(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    file: UploadFile,
    action: Annotated[UploadAttachmentAction, Depends(melding_upload_attachment_action)],
) -> AttachmentOutput:
    # When uploading a file without filename, Starlette gives us a string instead of an instance of UploadFile,
    # so actually the filename will always be available. To satisfy the type checker we assert that is the case.
    assert file.filename is not None
    assert file.content_type is not None

    data_header = await file.read(2048)
    await file.seek(0)

    async def iterate() -> AsyncIterator[bytes]:
        while chunk := await file.read(1024 * 1024):
            yield chunk

    try:
        attachment = await action(melding_id, token, file.filename, file.content_type, data_header, iterate())
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
    except MediaTypeNotAllowed:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Attachment not allowed")
    except MediaTypeIntegrityError:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Media type of data does not match provided media type"
        )

    return _hydrate_attachment_output(attachment)


@router.get(
    "/{melding_id}/attachment/{attachment_id}/download",
    name="melding:attachment-download",
    responses={
        **not_found_response,
        **unauthorized_response,
    },
)
async def download_attachment(
    action: Annotated[DownloadAttachmentAction, Depends(melding_download_attachment_action)],
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    attachment_id: Annotated[int, Path(description="The id of the attachment.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    _type: Annotated[
        AttachmentTypes,
        Query(
            alias="type",
            description="The type of the attachment to download.",
        ),
    ] = AttachmentTypes.ORIGINAL,
) -> StreamingResponse:
    try:
        iterator = await action(melding_id, attachment_id, token, _type)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return StreamingResponse(iterator)


@router.get(
    "/{melding_id}/attachments",
    name="melding:attachments",
    responses={**not_found_response, **unauthorized_response},
)
async def list_attachments(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[ListAttachmentsAction, Depends(melding_list_attachments_action)],
) -> list[AttachmentOutput]:
    try:
        attachments = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    output = []
    for attachment in attachments:
        output.append(_hydrate_attachment_output(attachment))

    return output


@router.delete(
    "/{melding_id}/attachment/{attachment_id}",
    name="melding:attachment-delete",
    responses={**not_found_response, **unauthorized_response},
)
async def delete_attachment(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    attachment_id: Annotated[int, Path(description="The id of the attachment.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[DeleteAttachmentAction, Depends(melding_delete_attachment_action)],
) -> None:
    try:
        await action(melding_id, attachment_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)


@router.post(
    "/{melding_id}/location",
    name="melding:add-location",
    responses={**not_found_response, **unauthorized_response},
)
async def add_location_to_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    location: GeoJson,
    action: Annotated[AddLocationToMeldingAction, Depends(melding_add_location_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:

    try:
        melding = await action(melding_id, token, location)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    return produce_output(melding)
