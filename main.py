import typer

from commands import azure, groups, meldingen, static_forms, users

app = typer.Typer()
app.add_typer(users.app, name="users")
app.add_typer(groups.app, name="groups")
app.add_typer(static_forms.app, name="static-forms")
app.add_typer(azure.app, name="azure")
app.add_typer(meldingen.app, name="meldingen")


if __name__ == "__main__":
    app()
