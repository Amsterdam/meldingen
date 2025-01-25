import pytest
import anyio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.database import DatabaseSessionManager

from tests.scenarios.conftest import async_to_sync
from pytest_bdd import given, when, then, parsers, scenario
import httpx
from typing import Any, AsyncIterator, Callable


@pytest.fixture
def melding() -> dict[str, Any]:
    return {}

@given(
    'I have a problem that I want to report',
    target_fixture='problem',
)
def given_i_am_on_the_melding_form() -> dict[str,str]:
    return {
        'text': 'I have a problem that I want to report'
    }

@when('I submit my problem to the primary form')
@async_to_sync
async def when_i_submit_the_primary_form(app, client: AsyncClient, problem: dict[str, str]) -> None:
    response = await client.post(app.url_path_for('melding:create'), json=problem)
    print(response)
    melding = response.json()
    print(melding)
    assert response.status_code == 201



@pytest.fixture
def geojson() -> dict[str, Any]:
    geometry = {"type": "Point", "coordinates": [52.3680605, 4.897092]}

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {},
    }


@when('I fill in the location of the problem')
@async_to_sync
async def when_i_fill_in_the_location_of_the_problem(client: AsyncClient, melding, geojson) -> None:
    response = await client.post(f"/melding/{melding['id']}/location", json=geojson, params={'token': melding['token']})
    assert response.status_code == 201


