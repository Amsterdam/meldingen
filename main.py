import typer

from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.models import User

app = typer.Typer()
container = Container()
container.settings.from_dict(Settings().model_dump())


@app.command()
def add_user(email: str) -> None:
    user_repository = container.user_repository()

    user = User()
    user.username = email
    user.email = email

    user_repository.add(user)


if __name__ == "__main__":
    app()
