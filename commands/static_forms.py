import asyncio
from typing import Annotated

import typer
from meldingen_core.exceptions import NotFoundException
from rich import print

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import (
    FormIoComponentTypeEnum,
    FormIoFormDisplayEnum,
    FormIoTextAreaComponent,
    StaticForm,
    StaticFormTypeEnum,
)
from meldingen.repositories import StaticFormRepository

app = typer.Typer()


async def async_create_static_forms() -> None:
    async for session in database_session(database_session_manager(database_engine())):
        static_form_repository = StaticFormRepository(session)

        for form_type in StaticFormTypeEnum:
            """
            Generate all forms based on form_type.
            Needs to be done more precise later.
            """

            try:
                await static_form_repository.retrieve_by_type(StaticFormTypeEnum[form_type])
                print(f"[red]Error[/red] - The {form_type} form already exists")
                continue
            except NotFoundException:
                # The primary from does not exist, let's create it!
                ...

            label = form_type.capitalize()

            form = StaticForm(
                type=StaticFormTypeEnum[form_type],
                title=f"{label}",
                display=FormIoFormDisplayEnum.form,
            )

            component = FormIoTextAreaComponent(
                label=f"{label}",
                description="",
                key=f"{form_type}",
                type=FormIoComponentTypeEnum.text_area,
                input=True,
                auto_expand=True,
                max_char_count=255,
            )

            components = await form.awaitable_attrs.components
            components.append(component)

            await static_form_repository.save(form)

        print("[green]Success[/green] - The primary form has been created")


@app.command()
def create() -> None:
    asyncio.run(async_create_static_forms())


if __name__ == "__main__":
    app()
