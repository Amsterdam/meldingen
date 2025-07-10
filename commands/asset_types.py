import asyncio
from typing import Any

import typer
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import AssetType
from meldingen.repositories import AssetTypeRepository
from meldingen.schemas.input import AssetTypeInput

app = typer.Typer()


async def async_add_asset_type(name: str, class_name: str, arguments: dict[str, Any]) -> None:
    async for session in database_session(database_session_manager(database_engine())):
        asset_type_repository = AssetTypeRepository(session)

        asset_type_input = AssetTypeInput(name=name, class_name=class_name, arguments=arguments)
        asset_type = AssetType(**asset_type_input.model_dump())

        try:
            await asset_type_repository.save(asset_type)
        except IntegrityError:
            print(f"[red]Error[/red] - Asset Type already exists!")
            raise typer.Exit

        print(f'[green]Success[/green] - Asset Type "{name}" created!')


@app.command()
def add(name: str, class_name: str, base_url: str | None) -> None:
    arguments = {"base_url": base_url} if base_url else {}
    asyncio.run(async_add_asset_type(name, class_name, arguments))


if __name__ == "__main__":
    app()
