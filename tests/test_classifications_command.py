from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from commands.classifications import ensure_fallback_classification
from meldingen.config import settings


@pytest.mark.anyio
async def test_ensure_fallback_classification_uses_idempotent_upsert() -> None:
    """The fallback classification must be inserted with ON CONFLICT DO NOTHING so
    it is created when missing and left untouched when it already exists — always
    present regardless of which other classifications the environment has."""
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = 1
    session.execute.return_value = result

    created = await ensure_fallback_classification(session)

    assert created == 1
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()

    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    sql = str(compiled)

    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql
    assert compiled.params["name"] == settings.llm_fallback_classification_name
    assert compiled.params["instructions"] == settings.llm_fallback_classification_instructions


def test_fallback_classification_defaults_present() -> None:
    """Defaults guarantee the fallback appears even without any env override."""
    assert settings.llm_fallback_classification_name == "Overige"
    assert settings.llm_fallback_classification_instructions
