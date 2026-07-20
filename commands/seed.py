import asyncio
import json
from typing import Final

import typer
from rich import print
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Classification
from meldingen.schemas.input import ClassificationCreateInput

app = typer.Typer()

CLASSIFICATION_SEED_FILE_PATH: Final[str] = "./seed/classifications.json"


@app.command()
def seed(dry_run: bool = False) -> None:
    asyncio.run(async_seed_classification_from_file(CLASSIFICATION_SEED_FILE_PATH, dry_run))


def build_classification_insert(values: list[dict[str, str | None]]) -> Insert:
    """Build the insert-if-missing statement for the given classification values.

    On a conflicting ``name`` nothing happens: the existing classification (including its
    ``instructions``, ``asset_type`` and ``form``) is left untouched.
    """
    stmt = insert(Classification).values(values)
    return stmt.on_conflict_do_nothing(index_elements=["name"])


async def insert_missing_classifications(
    session: AsyncSession, values: list[dict[str, str | None]], dry_run: bool
) -> tuple[int, int]:
    """Insert classifications whose ``name`` is not yet present, and return (created, skipped).

    Existing classifications are never modified or deleted — if a ``name`` already exists it is
    left exactly as-is. When ``dry_run`` is True the counts are computed but nothing is written.
    """
    result = await session.execute(select(Classification.name))
    existing = {name for (name,) in result.all()}

    to_create = [value for value in values if value["name"] not in existing]
    created = len(to_create)
    skipped = len(values) - created

    if not dry_run and to_create:
        await session.execute(build_classification_insert(to_create))
        await session.commit()

    return created, skipped


def load_classification_values(file_path: str) -> list[dict[str, str | None]]:
    """Read and validate the seed file into a list of ``{"name", "instructions"}`` values."""
    try:
        with open(file_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"🟡 - Seeding of classsifactions aborted: no seed file found. ")
        raise typer.Exit

    if not isinstance(data, list):
        print(f"🔴 - Invalid data format in {file_path}. Expected a list of classifications.")
        raise typer.Exit

    values: list[dict[str, str | None]] = []
    for item in data:
        input = ClassificationCreateInput(**item)
        values.append({"name": input.name, "instructions": input.instructions})
    return values


async def async_seed_classification_from_file(file_path: str, dry_run: bool) -> None:
    """Idempotently seed classifications from the seed file.

    Classifications are matched by their unique ``name``: entries whose name is not yet in the
    database are inserted, and entries that already exist are left untouched (never updated,
    never deleted). This makes the command safe to run on every startup regardless of which
    classifications are already present.
    """
    values = load_classification_values(file_path)

    async for session in database_session(database_session_manager(database_engine())):
        created, skipped = await insert_missing_classifications(session, values, dry_run)

        verb = "would have seeded" if dry_run else "seeded"
        prefix = "Dry run - " if dry_run else "Success - "
        print(
            f"🟢 - {prefix}{verb} {len(values)} classifications from {file_path} "
            f"(created {created}, skipped {skipped} already present)."
        )


if __name__ == "__main__":
    app()
