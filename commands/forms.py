import asyncio
from typing import Annotated

import typer
from rich import print

from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.models import FormIoFormDisplayEnum, FormIoPrimaryForm

app = typer.Typer()
container = Container()
container.settings.from_dict(Settings().model_dump())


async def async_add_primary_form(title: str) -> None:
    form_repository = await container.form_repository()

    # Check if a primary form already exists
    if await form_repository.retrieve_primary_form():
        print("[red]Error[/red] - A primary form already exists")
        raise typer.Exit

    # Create the primary form
    primary_form = FormIoPrimaryForm(title=title, display=FormIoFormDisplayEnum.form, is_primary=True)
    await form_repository.save(primary_form)

    print(f'[green]Success[/green] - Primary Form "{title}" created!')


@app.command()
def add_primary(title: Annotated[str, typer.Option(prompt=True, help="The title of the primary form")]) -> None:
    asyncio.run(async_add_primary_form(title))


if __name__ == "__main__":
    app()
