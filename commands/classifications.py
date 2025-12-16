import asyncio
import json

import typer
from rich import print
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Classification
from meldingen.schemas.input import ClassificationCreateInput

app = typer.Typer()


@app.command()
def seed(file_path: str = "./seed/classifications.json", dry_run: bool = False) -> None:
    asyncio.run(async_seed_classification_from_file(file_path, dry_run))


async def async_seed_classification_from_file(file_path: str, dry_run: bool) -> None:
    try:
        with open(file_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"🟡 - Seeding of classsifactions aborted: no seed file found. ")
        raise typer.Exit

    if not isinstance(data, list):
        print(f"🔴 - Invalid data format in {file_path}. Expected a list of classifications.")
        raise typer.Exit

    models = []

    for item in data:
        input = ClassificationCreateInput(**item)
        classification = Classification(**input.model_dump())
        models.append(classification)

    async for session in database_session(database_session_manager(database_engine())):
        try:
            if dry_run is False:
                session.add_all(models)
                await session.commit()
                print(f"🟢 - Success - seeded {len(models)} classifications from {file_path}.")
            else:
                print(f"🟢 - Dry run - would have seeded {len(models)} classifications from {file_path}.")
        except IntegrityError:
            print(f"🟡 - Seeding of classifications aborted: found classifications already in database")
            raise typer.Exit


if __name__ == "__main__":
    app()
