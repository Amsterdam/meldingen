import asyncio

import typer

from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.models import User, UserCreateInput

app = typer.Typer()
container = Container()
container.settings.from_dict(Settings().model_dump())


async def async_add_user(email: str) -> None:
    user_repository = await container.user_repository()

    user_input = UserCreateInput(username=email, email=email)
    user = User.model_validate(user_input)

    await user_repository.add(user)


@app.command()
def add_user(email: str) -> None:
    asyncio.run(async_add_user(email))


if __name__ == "__main__":
    app()
