import typer

from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.models import User, UserInput

app = typer.Typer()
container = Container()
container.settings.from_dict(Settings().model_dump())


@app.command()
def add_user(email: str) -> None:
    user_repository = container.user_repository()

    user_input = UserInput(username=email, email=email)
    user = User.model_validate(user_input)

    user_repository.add(user)


if __name__ == "__main__":
    app()
