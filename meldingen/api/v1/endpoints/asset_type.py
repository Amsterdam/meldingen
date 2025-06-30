from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from meldingen.actions import AssetTypeCreateAction
from meldingen.authentication import authenticate_user
from meldingen.dependencies import asset_type_create_action
from meldingen.models import AssetType
from meldingen.schemas.input import AssetTypeInput
from meldingen.schemas.output import AssetTypeOutput

router = APIRouter()


@router.post(
    "/",
    name="asset-type:create",
    status_code=HTTP_201_CREATED,
    dependencies=[Depends(authenticate_user)],
)
async def create_asset_type(
    input: AssetTypeInput,
    action: Annotated[AssetTypeCreateAction, Depends(asset_type_create_action)],
) -> AssetTypeOutput:
    asset_type = AssetType(**input.model_dump())

    await action(asset_type)

    return AssetTypeOutput(
        id=asset_type.id,
        name=asset_type.name,
        class_name=asset_type.class_name,
        created_at=asset_type.created_at,
        updated_at=asset_type.updated_at,
    )
