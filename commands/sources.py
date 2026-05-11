import asyncio
from typing import Any, cast

import typer
from sqlalchemy import CursorResult
from sqlalchemy.dialects.postgresql import insert

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Source

app = typer.Typer()


initial_source_names = [
    "Telefoon – Adoptant",
    "Telefoon – ASC",
    "Telefoon – CCA",
    "Telefoon – CCTR",
    "Telefoon – Interswitch",
    "Telefoon – Stadsdeel",
    "E-mail – CCA",
    "E-mail – ASC",
    "E-mail – Stadsdeel",
    "Webcare – CCA",
    "Interne melding",
    "Fixi Weesp",
    "Meldkamer burger/ondernemer",
    "Meldkamer Handhaver",
    "Meldkamer Politie",
    "VerbeterDeBuurt",
    "Waarnemingenapp",
    "online",
    "TechView",
    "Telefoon - CCTR",
    "public-api",
    "app",
    "Chat - CCA",
    "Automatische signalering",
]


async def create_initial_sources() -> None:
    async for session in database_session(database_session_manager(database_engine())):
        stmt = insert(Source).values([{"name": name} for name in initial_source_names])
        stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
        result = cast(CursorResult[Any], await session.execute(stmt))
        await session.commit()
        typer.echo(f"✅ - Created {result.rowcount} new source(s), skipped existing")


@app.command()
def create() -> None:
    asyncio.run(create_initial_sources())
