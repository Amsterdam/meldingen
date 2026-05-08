import asyncio

import typer
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Source

app = typer.Typer()


initial_sources = [
    Source(name="Telefoon – Adoptant"),
    Source(name="Telefoon – ASC"),
    Source(name="Telefoon – CCA"),
    Source(name="Telefoon – CCTR"),
    Source(name="Telefoon – Interswitch"),
    Source(name="Telefoon – Stadsdeel"),
    Source(name="E-mail – CCA"),
    Source(name="E-mail – ASC"),
    Source(name="E-mail – Stadsdeel"),
    Source(name="Webcare – CCA"),
    Source(name="Interne melding"),
    Source(name="Fixi Weesp"),
    Source(name="Meldkamer burger/ondernemer"),
    Source(name="Meldkamer Handhaver"),
    Source(name="Meldkamer Politie"),
    Source(name="VerbeterDeBuurt"),
    Source(name="Waarnemingenapp"),
    Source(name="online"),
    Source(name="TechView"),
    Source(name="Telefoon - CCTR"),
    Source(name="public-api"),
    Source(name="app"),
    Source(name="Chat - CCA"),
    Source(name="Automatische signalering"),
]


async def create_initial_sources() -> None:
    async for session in database_session(database_session_manager(database_engine())):
        try:
            session.add_all(initial_sources)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            typer.echo("🟡 - Initial sources have already been created, skipping")
            raise typer.Exit

    typer.echo("✅ - Initial sources have been created")


@app.command()
def create() -> None:
    asyncio.run(create_initial_sources())
