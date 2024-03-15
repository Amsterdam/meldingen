from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path
from meldingen_core.actions.melding import MeldingCompleteAction, MeldingCreateAction, MeldingProcessAction
from meldingen_core.exceptions import NotFoundException
from mp_fsm.statemachine import WrongStateException
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from meldingen.actions import MeldingListAction, MeldingRetrieveAction
from meldingen.api.utils import PaginationParams, pagination_params
from meldingen.api.v1 import default_response, not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Melding, User
from meldingen.schemas import MeldingInput, MeldingOutput

router = APIRouter()


def _hydrate_output(melding: Melding) -> MeldingOutput:
    return MeldingOutput(
        id=melding.id,
        text=melding.text,
        state=melding.state,
        classification=melding.classification_id
    )


@router.post("/", name="melding:create", status_code=HTTP_201_CREATED)
@inject
async def create_melding(
    melding_input: MeldingInput,
    action: MeldingCreateAction[Melding, Melding] = Depends(Provide(Container.melding_create_action)),
) -> MeldingOutput:
    melding = Melding(**melding_input.model_dump())
    try:
        await action(melding)
    except NotFoundException:
        # TODO: The classifier received a classification name that does not exist
        ...

    return _hydrate_output(melding)


@router.get("/", name="melding:list", responses={**unauthorized_response})
@inject
async def list_meldingen(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    user: Annotated[User, Depends(authenticate_user)],
    action: MeldingListAction = Depends(Provide(Container.melding_list_action)),
) -> list[MeldingOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    meldingen = await action(limit=limit, offset=offset)
    output = []
    for melding in meldingen:
        output.append(_hydrate_output(melding))

    return output


@router.get("/{melding_id}", name="melding:retrieve", responses={**unauthorized_response, **not_found_response})
@inject
async def retrieve_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    user: Annotated[User, Depends(authenticate_user)],
    action: MeldingRetrieveAction = Depends(Provide(Container.melding_retrieve_action)),
) -> MeldingOutput:
    melding = await action(pk=melding_id)

    if not melding:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return _hydrate_output(melding)


@router.put(
    "/{melding_id}/process",
    name="melding:process",
    responses={
        HTTP_400_BAD_REQUEST: {
            "description": "Transition not allowed from current state",
            "content": {"application/json": {"example": {"detail": "Transition not allowed from current state"}}},
        },
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
        HTTP_400_BAD_REQUEST: {
            "description": "Transition not allowed from current state",
            "content": {"application/json": {"example": {"detail": "Transition not allowed from current state"}}},
        },
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
