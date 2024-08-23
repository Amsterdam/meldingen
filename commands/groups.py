import asyncio

import typer
from rich import print

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import Group
from meldingen.repositories import GroupRepository

app = typer.Typer()


async def async_add_group(name: str) -> None:
    async for session in database_session(database_session_manager(database_engine())):
        group_repository = GroupRepository(session)

        await group_repository.save(Group(name=name))

        print(f'[green]Success[/green] - Group "{name}" created!')


@app.command()
def add(name: str) -> None:
    asyncio.run(async_add_group(name))


if __name__ == "__main__":
    app()
