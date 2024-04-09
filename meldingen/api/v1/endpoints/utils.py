import os
from functools import partial
from typing import Annotated

from dependency_injector.wiring import inject
from fastapi import APIRouter
from geojson_pydantic import Point
from pydantic import AfterValidator, BaseModel

from meldingen.validators import load_geojson, within_polygon

router = APIRouter()


file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..", "GM0363.geojson")
within_polygon_validator = partial(within_polygon, shape=load_geojson(file_path))


class InMunicipalityInput(BaseModel):
    point: Annotated[Point, AfterValidator(within_polygon_validator)]


@router.post("/in-municipality", name="utils:in-municipality")
@inject
async def in_municipality(
    in_municipality_input: InMunicipalityInput,
) -> dict[str, bool]:
    return {"in_municipality": True}
