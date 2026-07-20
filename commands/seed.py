import asyncio
import json
from typing import Final

import typer
from rich import print
from sqlalchemy import func, select
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


def build_classification_upsert(values: list[dict[str, str | None]]) -> Insert:
    """Build the idempotent upsert statement for the given classification values.

    Inserts missing classifications and, on a conflicting ``name``, updates the
    ``instructions`` (leaving any existing ``asset_type``/``form`` untouched).
    """
    stmt = insert(Classification).values(values)
    return stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={"instructions": stmt.excluded.instructions, "updated_at": func.now()},
    )


async def upsert_classifications(
    session: AsyncSession, values: list[dict[str, str | None]], dry_run: bool
) -> tuple[int, int, int]:
    """Upsert classifications by name and return the (created, updated, unchanged) counts.

    Existing classifications are matched on their unique ``name``. Nothing is ever deleted:
    classifications not present in ``values`` are left as-is. When ``dry_run`` is True the
    counts are computed but no changes are written.
    """
    result = await session.execute(select(Classification.name, Classification.instructions))
    existing = {name: instructions for name, instructions in result.all()}

    created = sum(1 for value in values if value["name"] not in existing)
    updated = sum(
        1 for value in values if value["name"] in existing and existing[value["name"]] != value["instructions"]
    )
    unchanged = len(values) - created - updated

    if not dry_run and values:
        await session.execute(build_classification_upsert(values))
        await session.commit()

    return created, updated, unchanged


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
    """Idempotently reconcile the classifications in the database with the seed file.

    Each entry is upserted by its unique ``name``: missing classifications are inserted and
    existing ones have their ``instructions`` updated. Classifications that are no longer in
    the file are left untouched (never deleted), so the command is safe to run on every
    startup regardless of which classifications are already present.
    """
    values = load_classification_values(file_path)

    async for session in database_session(database_session_manager(database_engine())):
        created, updated, unchanged = await upsert_classifications(session, values, dry_run)

        verb = "would have seeded" if dry_run else "seeded"
        prefix = "Dry run - " if dry_run else "Success - "
        print(
            f"🟢 - {prefix}{verb} {len(values)} classifications from {file_path} "
            f"(created {created}, updated {updated}, unchanged {unchanged})."
        )


if __name__ == "__main__":
    app()
