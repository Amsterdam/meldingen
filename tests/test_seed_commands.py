import json

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from commands.seed import (
    build_classification_insert,
    insert_missing_classifications,
    load_classification_values,
)
from meldingen.models import Classification

EXAMPLE_FILE_PATH = "./seed/examples/classifications.json"


def test_load_classification_values_reads_all_entries() -> None:
    with open(EXAMPLE_FILE_PATH) as f:
        expected = len(json.load(f))

    values = load_classification_values(EXAMPLE_FILE_PATH)

    assert len(values) == expected
    assert all(set(value) == {"name", "instructions"} for value in values)


def test_build_classification_insert_uses_on_conflict_do_nothing() -> None:
    """Seeding must be idempotent and never touch existing rows: on a conflicting name, nothing."""
    stmt = build_classification_insert([{"name": "Test", "instructions": "Some instructions"}])

    sql = str(stmt.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]

    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql


@pytest.mark.anyio
async def test_insert_missing_classifications_is_idempotent(db_session: AsyncSession, test_database: None) -> None:
    values: list[dict[str, str | None]] = [
        {"name": "Seedtest A", "instructions": "one"},
        {"name": "Seedtest B", "instructions": "two"},
    ]

    # First run inserts both.
    assert await insert_missing_classifications(db_session, values, dry_run=False) == (2, 0)

    # Re-running with the same data changes nothing; both are skipped.
    assert await insert_missing_classifications(db_session, values, dry_run=False) == (0, 2)


@pytest.mark.anyio
async def test_insert_missing_leaves_existing_instructions_untouched(
    db_session: AsyncSession, test_database: None
) -> None:
    values: list[dict[str, str | None]] = [{"name": "Seedtest C", "instructions": "original"}]
    assert await insert_missing_classifications(db_session, values, dry_run=False) == (1, 0)

    # A later seed with changed instructions for the same name must NOT overwrite.
    values[0]["instructions"] = "changed"
    assert await insert_missing_classifications(db_session, values, dry_run=False) == (0, 1)

    result = await db_session.execute(
        select(Classification.instructions).where(Classification.name == "Seedtest C")
    )
    assert result.scalar_one() == "original"


@pytest.mark.anyio
async def test_insert_missing_dry_run_writes_nothing(db_session: AsyncSession, test_database: None) -> None:
    values: list[dict[str, str | None]] = [{"name": "Seedtest Dry", "instructions": "x"}]

    assert await insert_missing_classifications(db_session, values, dry_run=True) == (1, 0)
    # Still counts as new on a real run, proving the dry run persisted nothing.
    assert await insert_missing_classifications(db_session, values, dry_run=False) == (1, 0)
