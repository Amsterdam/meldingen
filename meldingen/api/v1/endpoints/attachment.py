from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from meldingen_core.actions.attachment import AttachmentTypes
from meldingen_core.exceptions import NotFoundException
from starlette.responses import StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND

from meldingen.actions import DownloadAttachmentAction
from meldingen.api.v1 import image_data_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import download_attachment_action

router = APIRouter()


@router.get(
    "/{id}",
    name="attachment:download",
    responses={**image_data_response, **unauthorized_response, **not_found_response},
    response_class=StreamingResponse,
    dependencies=[Depends(authenticate_user)],
)
async def download_attachment(
    action: Annotated[DownloadAttachmentAction, Depends(download_attachment_action)],
    attachment_id: Annotated[int, Path(description="The id of the attachment.", ge=1)],
    _type: Annotated[
        AttachmentTypes,
        Query(
            alias="type",
            description="The type of the attachment to download.",
        ),
    ] = AttachmentTypes.ORIGINAL,
) -> StreamingResponse:
    try:
        iterator, media_type = await action(attachment_id, _type)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return StreamingResponse(iterator, media_type=media_type)
