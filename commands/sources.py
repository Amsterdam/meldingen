import asyncio

import typer
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Source

app = typer.Typer()


initial_sources = [
    Source(name="Telefoon"),
    Source(name="E-mail"),
    Source(name="Balie"),
    Source(name="Brief"),
    Source(name="Sociale media"),
    Source(name="Website"),
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
