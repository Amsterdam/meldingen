import json

import pytest
from _pytest.capture import CaptureFixture
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from commands.seed import (
    async_seed_classification_from_file,
    build_classification_upsert,
    upsert_classifications,
)

EXAMPLE_FILE_PATH = "./seed/examples/classifications.json"


@pytest.mark.anyio
async def test_seed_classifications_dry_run_reports_total(capsys: CaptureFixture[str]) -> None:
    with open(EXAMPLE_FILE_PATH) as f:
        expected = len(json.load(f))

    await async_seed_classification_from_file(EXAMPLE_FILE_PATH, dry_run=True)

    # rich may wrap the line, so normalise whitespace before asserting.
    out = " ".join(capsys.readouterr().out.split())
    assert f"Dry run - would have seeded {expected} classifications" in out


def test_build_classification_upsert_uses_on_conflict_do_update() -> None:
    """Seeding must be idempotent: an existing name updates instructions rather than erroring."""
    stmt = build_classification_upsert([{"name": "Test", "instructions": "Some instructions"}])

    sql = str(stmt.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]

    assert "ON CONFLICT" in sql
    assert "DO UPDATE" in sql


@pytest.mark.anyio
async def test_upsert_classifications_is_idempotent(db_session: AsyncSession, test_database: None) -> None:
    values: list[dict[str, str | None]] = [
        {"name": "Seedtest A", "instructions": "one"},
        {"name": "Seedtest B", "instructions": "two"},
    ]

    # First run inserts both.
    assert await upsert_classifications(db_session, values, dry_run=False) == (2, 0, 0)

    # Re-running with the same data changes nothing.
    assert await upsert_classifications(db_session, values, dry_run=False) == (0, 0, 2)

    # Changing an instruction updates that one and leaves the other unchanged.
    values[0]["instructions"] = "changed"
    assert await upsert_classifications(db_session, values, dry_run=False) == (0, 1, 1)


@pytest.mark.anyio
async def test_upsert_classifications_dry_run_writes_nothing(db_session: AsyncSession, test_database: None) -> None:
    values: list[dict[str, str | None]] = [{"name": "Seedtest Dry", "instructions": "x"}]

    assert await upsert_classifications(db_session, values, dry_run=True) == (1, 0, 0)
    # Still counts as new on a real run, proving the dry run persisted nothing.
    assert await upsert_classifications(db_session, values, dry_run=False) == (1, 0, 0)
