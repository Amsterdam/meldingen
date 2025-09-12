import logging
from typing import Annotated, Any, AsyncIterator, Sequence

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry
from meldingen_core.actions.attachment import AttachmentTypes
from meldingen_core.actions.melding import (
    MelderMeldingListQuestionsAnswersAction,
    MeldingAddAttachmentsAction,
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingContactInfoAddedAction,
    MeldingCreateAction,
    MeldingListQuestionsAnswersAction,
    MeldingProcessAction,
    MeldingSubmitLocationAction,
    MeldingUpdateAction,
)
from meldingen_core.exceptions import NotFoundException
from meldingen_core.filters import MeldingListFilters
from meldingen_core.statemachine import MeldingBackofficeStates, MeldingStates, get_all_backoffice_states
from meldingen_core.token import TokenException
from meldingen_core.validators import MediaTypeIntegrityError, MediaTypeNotAllowed
from mp_fsm.statemachine import GuardException, WrongStateException
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.actions.attachment import (
    DeleteAttachmentAction,
    ListAttachmentsAction,
    MelderDownloadAttachmentAction,
    MelderListAttachmentsAction,
    UploadAttachmentAction,
)
from meldingen.actions.form import AnswerCreateAction, AnswerUpdateAction
from meldingen.actions.melding import (
    AddContactInfoToMeldingAction,
    AddLocationToMeldingAction,
    MelderMeldingRetrieveAction,
    MeldingAddAssetAction,
    MeldingDeleteAssetAction,
    MeldingGetPossibleNextStatesAction,
    MeldingListAction,
    MeldingRetrieveAction,
    MeldingSubmitAction,
)
from meldingen.api.utils import ContentRangeHeaderAdder, PaginationParams, SortParams, pagination_params, sort_param
from meldingen.api.v1 import (
    default_response,
    image_data_response,
    list_response,
    not_found_response,
    transition_not_allowed,
    unauthorized_response,
)
from meldingen.authentication import authenticate_user
from meldingen.dependencies import (
    answer_output_factory,
    melder_melding_download_attachment_action,
    melder_melding_list_attachments_action,
    melder_melding_list_questions_and_answers_action,
    melder_melding_retrieve_action,
    melding_add_asset_action,
    melding_add_attachments_action,
    melding_add_contact_action,
    melding_add_location_action,
    melding_answer_create_action,
    melding_answer_questions_action,
    melding_answer_update_action,
    melding_complete_action,
    melding_contact_info_added_action,
    melding_create_action,
    melding_create_output_factory,
    melding_delete_asset_action,
    melding_delete_attachment_action,
    melding_get_possible_next_states_action,
    melding_list_action,
    melding_list_attachments_action,
    melding_list_questions_and_answers_action,
    melding_list_questions_and_answers_output_factory,
    melding_output_factory,
    melding_primary_form_validator,
    melding_process_action,
    melding_repository,
    melding_retrieve_action,
    melding_submit_action,
    melding_submit_location_action,
    melding_update_action,
    melding_update_output_factory,
    melding_upload_attachment_action,
    public_id_generator,
    states_output_factory,
)
from meldingen.exceptions import MeldingNotClassifiedException
from meldingen.generators import PublicIdGenerator
from meldingen.models import Answer, Attachment, Classification, Melding
from meldingen.repositories import MeldingRepository
from meldingen.schemas.input import (
    AnswerInput,
    CompleteMeldingInput,
    MeldingAssetInput,
    MeldingContactInput,
    MeldingInput,
)
from meldingen.schemas.output import (
    AnswerOutput,
    AnswerQuestionOutput,
    AttachmentOutput,
    MeldingCreateOutput,
    MeldingOutput,
    MeldingUpdateOutput,
    StatesOutput,
)
from meldingen.schemas.output_factories import (
    AnswerListOutputFactory,
    AnswerOutputFactory,
    MeldingCreateOutputFactory,
    MeldingOutputFactory,
    MeldingUpdateOutputFactory,
    StatesOutputFactory,
)
from meldingen.schemas.types import GeoJson
from meldingen.validators import MeldingPrimaryFormValidator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", name="melding:create", status_code=HTTP_201_CREATED)
async def create_melding(
    melding_input: MeldingInput,
    action: Annotated[MeldingCreateAction[Melding, Classification], Depends(melding_create_action)],
    validate_using_jsonlogic: Annotated[MeldingPrimaryFormValidator, Depends(melding_primary_form_validator)],
    generate_public_id: Annotated[PublicIdGenerator, Depends(public_id_generator)],
    produce_output: Annotated[MeldingCreateOutputFactory, Depends(melding_create_output_factory)],
) -> MeldingCreateOutput:
    melding_dict = melding_input.model_dump()

    await validate_using_jsonlogic(melding_dict)

    melding = Melding(**melding_dict)

    while True:
        melding.public_id = generate_public_id()
        try:
            await action(melding)
        except IntegrityError:
            continue

        break

    return produce_output(melding)


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
    in_area: Annotated[str, Query(description="Geometry which the melding location should reside in.")] | None = None,
    state: (
        Annotated[
            str,
            Query(
                example=f"{MeldingStates.PROCESSING},{MeldingStates.COMPLETED}",
                description="Comma-seperated list of states that the melding should have. If left empty, meldingen will be filtered by backoffice states.",
            ),
        ]
        | None
    ) = None,
) -> list[MeldingOutput]:
    area = None
    if in_area is not None:
        try:
            feature: Feature[Geometry, dict[str, Any] | BaseModel] = Feature.model_validate_json(in_area)
        except ValidationError as e:
            raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, e.errors()) from e

        if feature.geometry is not None:
            area = feature.geometry.model_dump_json()

    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    states: Sequence[MeldingBackofficeStates] = (
        [MeldingBackofficeStates(s) for s in state.split(",") if s in MeldingBackofficeStates]
        if state
        else get_all_backoffice_states()
    )

    meldingen = await action(
        limit=limit,
        offset=offset,
        sort_attribute_name=sort.get_attribute_name(),
        sort_direction=sort.get_direction(),
        filters=MeldingListFilters(
            area=area,
            states=states,
        ),
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


@router.get(
    "/{melding_id}/melder",
    name="melding:retrieve_melder",
    responses={**unauthorized_response, **not_found_response},
)
async def retrieve_melding_melder(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MelderMeldingRetrieveAction, Depends(melder_melding_retrieve_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

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
    validate_using_jsonlogic: Annotated[MeldingPrimaryFormValidator, Depends(melding_primary_form_validator)],
    action: Annotated[MeldingUpdateAction[Melding, Classification], Depends(melding_update_action)],
    produce_output: Annotated[MeldingUpdateOutputFactory, Depends(melding_update_output_factory)],
) -> MeldingUpdateOutput:
    melding_dict = melding_input.model_dump()

    await validate_using_jsonlogic(melding_dict)

    try:
        melding = await action(pk=melding_id, values=melding_dict, token=token)
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
    action: Annotated[MeldingAnswerQuestionsAction[Melding], Depends(melding_answer_questions_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except GuardException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="All required questions must be answered first")
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
    action: Annotated[MeldingAddAttachmentsAction[Melding], Depends(melding_add_attachments_action)],
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
    action: Annotated[MeldingSubmitLocationAction[Melding], Depends(melding_submit_location_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
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

    return produce_output(melding)


@router.put(
    "/{melding_id}/submit",
    name="melding:submit",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
)
async def melding_submit(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MeldingSubmitAction, Depends(melding_submit_action)],
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
    action: Annotated[MeldingProcessAction[Melding], Depends(melding_process_action)],
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
    action: Annotated[MeldingCompleteAction[Melding], Depends(melding_complete_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
    input: CompleteMeldingInput | None = None,
) -> MeldingOutput:
    mail_text = None
    if input is not None:
        mail_text = input.mail_body

    try:
        melding = await action(melding_id, mail_text)
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
    produce_output: Annotated[AnswerOutputFactory, Depends(answer_output_factory)],
) -> AnswerOutput:
    try:
        answer = await action(melding_id, token, question_id, answer_input)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
    except MeldingNotClassifiedException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Melding not classified")

    return produce_output(answer)


@router.patch(
    "/{melding_id}/answer/{answer_id}",
    name="melding:update-answer",
    responses={
        **not_found_response,
        **unauthorized_response,
        **{
            HTTP_400_BAD_REQUEST: {
                "description": "",
                "content": {
                    "application/json": {
                        "example": {"detail": [{"msg": "Answer does not belong to the melding."}]},
                    },
                },
            },
        },
    },
)
async def update_answer(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    answer_id: Annotated[int, Path(description="The id of the answer.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    answer_input: AnswerInput,
    action: Annotated[AnswerUpdateAction, Depends(melding_answer_update_action)],
    produce_output: Annotated[AnswerOutputFactory, Depends(answer_output_factory)],
) -> AnswerOutput:
    try:
        answer = await action(melding_id, token, answer_id, answer_input.text)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return produce_output(answer)


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
    response_class=StreamingResponse,
    responses={
        **image_data_response,
        **not_found_response,
        **unauthorized_response,
    },
)
async def melder_download_attachment(
    action: Annotated[MelderDownloadAttachmentAction, Depends(melder_melding_download_attachment_action)],
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
        iterator, media_type = await action(melding_id, attachment_id, token, _type)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return StreamingResponse(iterator, media_type=media_type)


@router.get(
    "/{melding_id}/attachments",
    name="melding:attachments",
    responses={**not_found_response, **unauthorized_response},
    dependencies=[Depends(authenticate_user)],
)
async def list_attachments(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[ListAttachmentsAction, Depends(melding_list_attachments_action)],
) -> list[AttachmentOutput]:
    attachments = await action(melding_id)

    output = []
    for attachment in attachments:
        output.append(_hydrate_attachment_output(attachment))

    return output


@router.get(
    "/{melding_id}/attachments/melder",
    name="melding:attachments_melder",
    responses={**not_found_response, **unauthorized_response},
)
async def melder_list_attachments(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MelderListAttachmentsAction, Depends(melder_melding_list_attachments_action)],
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


@router.patch(
    "/{melding_id}/location",
    name="melding:location-add",
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

    return produce_output(melding)


@router.patch(
    "/{melding_id}/contact",
    name="melding:contact-add",
    responses={**not_found_response, **unauthorized_response},
)
async def add_contact_to_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    contact_details: MeldingContactInput,
    action: Annotated[AddContactInfoToMeldingAction, Depends(melding_add_contact_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    phone, email = contact_details.phone, contact_details.email

    try:
        melding = await action(melding_id, phone, email, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return produce_output(melding)


@router.put(
    "/{melding_id}/add_contact_info",
    name="melding:add-contact-info",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
)
async def add_contact_info(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MeldingContactInfoAddedAction[Melding], Depends(melding_contact_info_added_action)],
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


@router.get(
    "/{melding_id}/answers/melder",
    name="melding:answers_melder",
    responses={
        **not_found_response,
        **unauthorized_response,
    },
)
async def melder_list_answers(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[
        MelderMeldingListQuestionsAnswersAction[Melding, Answer],
        Depends(melder_melding_list_questions_and_answers_action),
    ],
    produce_output: Annotated[AnswerListOutputFactory, Depends(melding_list_questions_and_answers_output_factory)],
) -> list[AnswerQuestionOutput]:
    try:
        answers = await action(melding_id, token)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except TokenException:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    return await produce_output(answers)


@router.get(
    "/{melding_id}/answers",
    name="melding:answers",
    dependencies=[Depends(authenticate_user)],
    responses={
        **not_found_response,
        **unauthorized_response,
    },
)
async def list_answers(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[
        MeldingListQuestionsAnswersAction[Answer],
        Depends(melding_list_questions_and_answers_action),
    ],
    produce_output: Annotated[AnswerListOutputFactory, Depends(melding_list_questions_and_answers_output_factory)],
) -> list[AnswerQuestionOutput]:
    answers = await action(melding_id)

    return await produce_output(answers)


@router.post(
    "/{melding_id}/asset",
    name="melding:add-asset",
    responses={**not_found_response, **unauthorized_response},
)
async def add_asset(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    input: MeldingAssetInput,
    action: Annotated[MeldingAddAssetAction, Depends(melding_add_asset_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id, input.external_id, input.asset_type_id, token)
    except NotFoundException as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e)) from e
    except TokenException as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED) from e

    return produce_output(melding)


@router.delete(
    "/{melding_id}/asset/{asset_id}",
    name="melding:delete-asset",
    responses={**not_found_response, **unauthorized_response},
)
async def delete_asset(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    asset_id: Annotated[int, Path(description="The id of the asset.", ge=1)],
    token: Annotated[str, Query(description="The token of the melding.")],
    action: Annotated[MeldingDeleteAssetAction, Depends(melding_delete_asset_action)],
) -> None:
    try:
        await action(melding_id, asset_id, token)
    except NotFoundException as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e)) from e
    except TokenException as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED) from e


@router.get(
    "/{melding_id}/next_possible_states",
    name="melding:next_possible_states",
    dependencies=[Depends(authenticate_user)],
    responses={
        **not_found_response,
        **unauthorized_response,
    },
)
async def next_possible_states(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[
        MeldingGetPossibleNextStatesAction,
        Depends(melding_get_possible_next_states_action),
    ],
    produce_output: Annotated[StatesOutputFactory, Depends(states_output_factory)],
) -> StatesOutput:
    try:
        states = await action(melding_id)
    except NotFoundException as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e)) from e

    return produce_output(states)
