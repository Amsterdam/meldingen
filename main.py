import typer

from commands import groups, users

app = typer.Typer()
app.add_typer(users.app, name="users")
app.add_typer(groups.app, name="groups")


if __name__ == "__main__":
    app()
