import typer

from commands import asset_types, azure, classifications, groups, meldingen, static_forms, users

app = typer.Typer()
app.add_typer(users.app, name="users")
app.add_typer(groups.app, name="groups")
app.add_typer(static_forms.app, name="static-forms")
app.add_typer(azure.app, name="azure")
app.add_typer(meldingen.app, name="meldingen")
app.add_typer(asset_types.app, name="asset_types")
app.add_typer(classifications.app, name="classifications")


if __name__ == "__main__":
    app()
