from typing import Any, Final

from fastapi import FastAPI
from httpx import AsyncClient
from pytest_bdd import given, parsers, then, when
from starlette.status import HTTP_200_OK

from tests.scenarios.conftest import async_step

ROUTE_NAME_LOCATION_ADD: Final[str] = "melding:location-add"


@given(
    parsers.parse("I know the latitude {lat:f} and longitude {lon:f} values of my melding"), target_fixture="geojson"
)
def i_know_the_latitude_and_longitude_values_of_my_melding(lat: float, lon: float) -> dict[str, Any]:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lat, lon]}, "properties": {}}


@when("I add the location as geojson to my melding", target_fixture="my_melding")
@async_step
async def i_supply_the_location_as_geojson_to_my_melding(
    my_melding: dict[str, Any], token: str, geojson: dict[str, float], app: FastAPI, client: AsyncClient
) -> dict[str, Any]:
    response = await client.post(
        app.url_path_for(ROUTE_NAME_LOCATION_ADD, melding_id=my_melding["id"]), params={"token": token}, json=geojson
    )
    assert response.status_code == HTTP_200_OK

    body = response.json()
    assert isinstance(body, dict)

    return body


@then("the location should be attached to the melding")
def then_location_should_be_attached_to_melding(my_melding: dict[str, Any], geojson: dict[str, Any]) -> None:
    assert geojson == my_melding["geo_location"]
