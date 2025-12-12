import asyncio
from typing import Any

import typer
from rich import print
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Classification
from meldingen.repositories import ClassificationRepository
from meldingen.schemas.input import ClassificationCreateInput
import json

app = typer.Typer()


async def async_add_classification(data: dict[str, Any]) -> None:
    async for session in database_session(database_session_manager(database_engine())):
        repository = ClassificationRepository(session)

        input = ClassificationCreateInput(**data)
        classification = Classification(**input.model_dump())

        try:
            await repository.save(classification)
        except IntegrityError:
            print(f"[yellow]Warning[/yellow] - Classification {classification.name} already exists!")
            raise typer.Exit

        print(f'[green]Success[/green] - Classification "{classification.name}" created!')


# @app.command()
# def add(name: str) -> None:
#     asyncio.run(async_add_classification({"name": name}))


@app.command()
def seed(file_path: str = "./seed/classifications.json") -> None:
    asyncio.run(async_seed_classification_from_file(file_path))


async def async_seed_classification_from_file(file_path: str) -> None:
    with open(file_path) as f:
        data = json.load(f)

    models = []

    for item in data:
        input = ClassificationCreateInput(**item)
        classification = Classification(**input.model_dump())
        models.append(classification)

    async with database_session(database_session_manager(database_engine())) as session:
        try:
            session.add_all(models)
            await session.commit()
            print(f'[green]Success[/green] - Seeded {len(models)} classifications from {file_path}!')
        except IntegrityError as e:
            print(f"[red]Error[/red] - {str(e)}")
            raise typer.Exit


if __name__ == "__main__":
    app()
