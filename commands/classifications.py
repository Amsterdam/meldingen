import asyncio

import typer
from pydantic.v1 import EmailStr
from rich import print
from sqlalchemy.exc import IntegrityError

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import User
from meldingen.repositories import GroupRepository, UserRepository, ClassificationRepository
from meldingen.schemas.input import UserCreateInput

app = typer.Typer()


async def async_add_classification(email: str) -> None:
    async for session in database_session(database_session_manager(database_engine())):
        user_repository = ClassificationRepository(session)

        user_input = UserCreateInput(username=email, email=EmailStr(email))
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




@app.command()
def seed() -> None:
    # check if file exists



if __name__ == "__main__":
    app()
