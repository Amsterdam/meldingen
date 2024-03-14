import typer

from commands import forms, groups, users

app = typer.Typer()
app.add_typer(users.app, name="users")
app.add_typer(groups.app, name="groups")
app.add_typer(forms.app, name="forms")


if __name__ == "__main__":
    app()
