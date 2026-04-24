import asyncio

import typer
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Label
from meldingen.repositories import LabelRepository

app = typer.Typer()


# Labels formerly known as types
initial_labels = [
    Label(name="Melding"),
    Label(name="Aanvraag"),
    Label(name="Vraag"),
    Label(name="Klacht"),
    Label(name="Grootonderhoud"),
    Label(name="Projectverzoek"),
]


async def create_initial_labels() -> None:
    async for session in database_session(database_session_manager(database_engine())):
        try:
            session.add_all(initial_labels)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            typer.echo("🟡 - Initial labels have already been created, skipping")
            raise typer.Exit

    typer.echo("✅ - Initial labels have been created")


@app.command()
def create() -> None:
    asyncio.run(create_initial_labels())
