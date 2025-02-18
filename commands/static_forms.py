import asyncio

import typer
from rich import print

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.models import (
    FormIoFormDisplayEnum,
    FormIoTextAreaComponent,
    StaticForm,
    StaticFormTypeEnum,
)
from meldingen.repositories import StaticFormRepository

app = typer.Typer()


async def create_primary_form(static_form_repository: StaticFormRepository) -> None:
    form = StaticForm(
        type=StaticFormTypeEnum.primary,
        title=StaticFormTypeEnum.primary.capitalize(),
        display=FormIoFormDisplayEnum.form,
    )
    form.components.append(
        FormIoTextAreaComponent(
            label="Wat wilt u melden?",
            description="Typ hieronder geen telefoonnummer en e-mailadres in. We vragen dit later in dit formulier.",
            key="primary",
            input=True,
            auto_expand=False,
            max_char_count=1000,
            jsonlogic=None,
            required=True,
        )
    )

    await static_form_repository.save(form)
    print("[green]Success[/green] - The primary form has been created")


async def create_attachments_form(static_form_repository: StaticFormRepository) -> None:
    form = StaticForm(
        type=StaticFormTypeEnum.attachments,
        title=StaticFormTypeEnum.attachments.capitalize(),
        display=FormIoFormDisplayEnum.form,
    )
    form.components.append(
        FormIoTextAreaComponent(
            label="Heeft u een foto om toe te voegen?",
            description="Voeg een foto toe om de situatie te verduidelijken. "
            "Verwijder alle persoonsgegevens van u en derden.\n\n"
            "- U kunt maximaal drie bestanden tegelijk toevoegen.\n"
            "- Toegestane bestandtypes: jpg, jpeg en png.\n"
            "- Een bestand mag maximaal 20 MB groot zijn.",
            key="file-upload",
            input=True,
            auto_expand=False,
            max_char_count=255,
            required=False,
        )
    )

    await static_form_repository.save(form)
    print("[green]Success[/green] - The attachments form has been created")


async def create_contact_form(static_form_repository: StaticFormRepository) -> None:
    form = StaticForm(
        type=StaticFormTypeEnum.contact,
        title=StaticFormTypeEnum.contact.capitalize(),
        display=FormIoFormDisplayEnum.form,
    )
    form.components.append(
        FormIoTextAreaComponent(
            label="Wat is uw e-mailadres?",
            description="",
            key="email-input",
            input=True,
            auto_expand=False,
            max_char_count=255,
            required=False,
        )
    )
    form.components.append(
        FormIoTextAreaComponent(
            label="Wat is uw e-mailadres?",
            description="",
            key="tel-input",
            input=True,
            auto_expand=False,
            max_char_count=255,
            required=False,
        )
    )

    await static_form_repository.save(form)
    print("[green]Success[/green] - The contact form has been created")


async def async_create_static_forms() -> None:
    async for session in database_session(database_session_manager(database_engine())):
        static_form_repository = StaticFormRepository(session)
        current_forms = await static_form_repository.list()
        current_form_types = [form.type for form in current_forms]

        if StaticFormTypeEnum.primary not in current_form_types:
            await create_primary_form(static_form_repository)

        if StaticFormTypeEnum.attachments not in current_form_types:
            await create_attachments_form(static_form_repository)

        if StaticFormTypeEnum.contact not in current_form_types:
            await create_contact_form(static_form_repository)


@app.command()
def create() -> None:
    asyncio.run(async_create_static_forms())


if __name__ == "__main__":
    app()
