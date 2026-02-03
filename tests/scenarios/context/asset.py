from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient, Response
from pytest_bdd import given, parsers, then, when
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from meldingen.models import Asset, AssetType, Classification, Melding
from tests.scenarios.conftest import async_step


@given(parsers.parse("there is an asset type {name:l} with max_assets {max_assets:d}"), target_fixture="asset_type")
@async_step
async def there_is_an_asset_type(name: str, max_assets: int, db_session: AsyncSession) -> AssetType:
    asset_type = AssetType(
        name=name, class_name="meldingen_core.assets.DummyAsset", arguments={}, max_assets=max_assets
    )

    db_session.add(asset_type)
    await db_session.commit()
    await db_session.refresh(asset_type)

    return asset_type


@given(
    parsers.parse("the classification {classification_name:l} has asset type {asset_type_name:l}"),
    target_fixture="classification",
)
@async_step
async def classification_has_asset_type(
    classification_name: str, asset_type_name: str, db_session: AsyncSession, asset_type: AssetType
) -> Classification:
    from sqlalchemy import select

    from meldingen.models import Classification

    # Fetch existing classification
    stmt = select(Classification).where(Classification.name == classification_name)
    result = await db_session.execute(stmt)
    classification = result.scalar_one()

    # Update with asset_type_id
    classification.asset_type_id = asset_type.id
    await db_session.commit()
    await db_session.refresh(classification)

    return classification


@when(parsers.parse('I add an asset with external_id "{external_id:S}" to my melding'), target_fixture="api_response")
@async_step
async def add_asset_to_melding(
    external_id: str, my_melding: dict[str, Any], asset_type: AssetType, app: FastAPI, client: AsyncClient
) -> Response:
    response = await client.post(
        app.url_path_for("melding:add-asset", melding_id=my_melding["id"]),
        params={"token": my_melding["token"]},
        json={"external_id": external_id, "asset_type_id": asset_type.id},
    )

    return response


@then("the asset should be added successfully", target_fixture="my_melding")
def asset_added_successfully(api_response: Response, my_melding: dict[str, Any]) -> dict[str, Any]:
    assert api_response.status_code == HTTP_200_OK

    body = api_response.json()
    assert isinstance(body, dict)
    assert body.get("id") == my_melding["id"]

    return body


@then(parsers.parse("the melding should have {count:d} asset(s)"))
@async_step
async def melding_should_have_assets_count(
    count: int, my_melding: dict[str, Any], app: FastAPI, client: AsyncClient
) -> None:
    response = await client.get(
        app.url_path_for("melding:assets_melder", melding_id=my_melding["id"]), params={"token": my_melding["token"]}
    )

    assert response.status_code == HTTP_200_OK
    assets = response.json()
    assert isinstance(assets, list)
    assert len(assets) == count


@then("I should be told that the maximum number of assets has been reached")
def max_assets_reached(api_response: Response) -> None:
    assert api_response.status_code == HTTP_400_BAD_REQUEST

    body = api_response.json()
    assert isinstance(body, dict)
    assert "maximum number of assets" in body.get("detail", "").lower()


@then("the asset addition should succeed")
def asset_addition_succeeds(api_response: Response) -> None:
    assert api_response.status_code == HTTP_200_OK
    body = api_response.json()
    assert isinstance(body, dict)


@when(
    parsers.parse('I remove the asset with external_id "{external_id:S}" from my melding'),
    target_fixture="api_response",
)
@async_step
async def remove_asset_from_melding(
    external_id: str, my_melding: dict[str, Any], app: FastAPI, client: AsyncClient
) -> Response:
    # First get the list of assets to find the asset_id
    list_response = await client.get(
        app.url_path_for("melding:assets_melder", melding_id=my_melding["id"]), params={"token": my_melding["token"]}
    )

    assert list_response.status_code == HTTP_200_OK
    assets = list_response.json()
    assert isinstance(assets, list)

    # Find the asset with the matching external_id
    asset_id = None
    for asset in assets:
        assert isinstance(asset, dict)
        if asset.get("external_id") == external_id:
            asset_id = asset.get("id")
            break

    assert asset_id is not None, f"Asset with external_id {external_id} not found"

    # Delete the asset
    response = await client.delete(
        app.url_path_for("melding:delete-asset", melding_id=my_melding["id"], asset_id=asset_id),
        params={"token": my_melding["token"]},
    )

    return response


@then("the asset should be removed successfully")
def asset_removed_successfully(api_response: Response) -> None:
    assert api_response.status_code == HTTP_200_OK
