import asyncio

import typer
from rich import print
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import User
from meldingen.repositories import GroupRepository, UserRepository
from meldingen.schemas import UserCreateInput

app = typer.Typer()


async def async_add_user(email: str) -> None:
    async for session in database_session(database_session_manager(database_engine())):
        user_repository = UserRepository(session)

        user_input = UserCreateInput(username=email, email=email)
        user = User(**user_input.model_dump())

        try:
            await user_repository.save(user)
        except IntegrityError:
            print(f"[red]Error[/red] - User already exists!")
            raise typer.Exit

        print(f'[green]Success[/green] - User "{email}" created!')


@app.command()
def add(email: str) -> None:
    asyncio.run(async_add_user(email))


async def async_add_user_to_group(email: str, group_name: str) -> None:
    async for session in database_session(database_session_manager(database_engine())):
        user_repository = UserRepository(session)
        group_repository = GroupRepository(session)

        user = await user_repository.find_by_email(email)
        group = await group_repository.find_by_name(group_name)

        user.groups.append(group)

        await user_repository.save(user)

        print(f'[green]Success[/green] - User "{email}" added to group "{group_name}"!')


@app.command()
def add_to_group(email: str, group_name: str) -> None:
    asyncio.run(async_add_user_to_group(email, group_name))


if __name__ == "__main__":
    app()
