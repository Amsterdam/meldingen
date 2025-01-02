import asyncio

import typer
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
        current_forms = await static_form_repository.list()
        current_form_types = [form.type for form in current_forms]

        for form_type in StaticFormTypeEnum:
            """
            Generate all forms based on form_type.
            Needs to be done more precise later.
            """

            if form_type in current_form_types:
                print(f"[red]Warning[/red] - The {form_type} form already exists")
                continue

            label = form_type.capitalize()

            form = StaticForm(
                type=StaticFormTypeEnum[form_type],
                title=f"{label}",
                display=FormIoFormDisplayEnum.form,
            )

            if form_type == StaticFormTypeEnum.primary:
                component = await generate_primary_form_component()
            else:
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

            print(f"[green]Success[/green] - The {form_type} form has been created")


async def generate_primary_form_component() -> FormIoTextAreaComponent:
    return FormIoTextAreaComponent(
        label="Wat wilt u melden?",
        description="Typ hieronder geen telefoonnummer en e-mailadres in. We vragen dit later in dit formulier.",
        key="primary",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        max_char_count=1000,
        jsonlogic=None,
        required=False,
    )


@app.command()
def create() -> None:
    asyncio.run(async_create_static_forms())


if __name__ == "__main__":
    app()
