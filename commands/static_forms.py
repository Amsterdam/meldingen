import asyncio
from typing import Annotated

import typer
from meldingen_core.exceptions import NotFoundException
from rich import print

from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.models import (
    FormIoComponent,
    FormIoComponentTypeEnum,
    FormIoFormDisplayEnum,
    StaticForm,
    StaticFormTypeEnum,
)

app = typer.Typer()
container = Container()
container.settings.from_dict(Settings().model_dump())


async def async_add_primary_form(title: str) -> None:
    static_form_repository = await container.static_form_repository()

    try:
        await static_form_repository.retrieve_by_type(StaticFormTypeEnum.primary)
        print("[red]Error[/red] - The primary form already exists")
        raise typer.Exit
    except NotFoundException:
        # The primary from does not exist, let's create it!
        ...

    primary_form = StaticForm(type=StaticFormTypeEnum.primary, title=title, display=FormIoFormDisplayEnum.form)

    component = FormIoComponent(
        label="Waar gaat het om?",
        description="",
        key="waar-gaat-het-om",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=False,
        show_char_count=True,
    )

    components = await primary_form.awaitable_attrs.components
    components.append(component)

    await static_form_repository.save(primary_form)

    print(f"[green]Success[/green] - The primary form has been created")


@app.command()
def add_primary(title: Annotated[str, typer.Option(prompt=True, help="The title of the primary form")]) -> None:
    asyncio.run(async_add_primary_form(title))


if __name__ == "__main__":
    app()
