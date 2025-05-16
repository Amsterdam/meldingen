from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from meldingen.actions import PreviewMailAction
from meldingen.api.v1 import unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.dependencies import preview_mail_action

router = APIRouter()


@router.post(
    "/preview",
    name="mail:preview",
    responses={**unauthorized_response},
    response_class=HTMLResponse,
    dependencies=[Depends(authenticate_user)],
)
async def preview(
    title: str,
    preview_text: str,
    body_text: str,
    action: Annotated[PreviewMailAction, Depends(preview_mail_action)],
) -> HTMLResponse:
    return HTMLResponse(await action(title, preview_text, body_text))
