import asyncio
from typing import Any, cast

import typer
from sqlalchemy import CursorResult
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.config import settings
from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Classification

app = typer.Typer()


async def ensure_fallback_classification(session: AsyncSession) -> int:
    """Idempotently insert the fallback classification.

    Uses `ON CONFLICT DO NOTHING` on the unique `name` column so the row is
    created when missing and left untouched when it already exists. Safe to run
    on every startup regardless of which other classifications are present.
    Returns the number of rows actually inserted (0 if it already existed).
    """
    stmt = insert(Classification).values(
        name=settings.llm_fallback_classification_name,
        instructions=settings.llm_fallback_classification_instructions,
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
    result = cast(CursorResult[Any], await session.execute(stmt))
    await session.commit()
    return result.rowcount


async def create_fallback_classification() -> None:
    async for session in database_session(database_session_manager(database_engine())):
        created = await ensure_fallback_classification(session)
        typer.echo(
            f"✅ - Ensured fallback classification '{settings.llm_fallback_classification_name}' "
            f"exists (created {created})"
        )


@app.command()
def ensure_fallback() -> None:
    asyncio.run(create_fallback_classification())
