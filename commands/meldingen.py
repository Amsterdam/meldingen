import asyncio

import typer
from meldingen_core.statemachine import MeldingStates
from rich import print

from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.repositories import MeldingRepository

app = typer.Typer()

DRAFT_MELDING_STATES = (
    MeldingStates.NEW,
    MeldingStates.CLASSIFIED,
    MeldingStates.QUESTIONS_ANSWERED,
    MeldingStates.ATTACHMENTS_ADDED,
    MeldingStates.LOCATION_SUBMITTED,
    MeldingStates.CONTACT_INFO_ADDED,
)


async def delete_expired_draft_meldingen() -> None:

    async for session in database_session(database_session_manager(database_engine())):
        melding_repository = MeldingRepository(session)

        result = await melding_repository.delete_with_expired_token_and_in_states(DRAFT_MELDING_STATES)

        counter = 0
        for melding in result:
            print(f"Deleted melding {melding.id} expired on {melding.token_expires} with state {melding.state}")

            counter += 1

        print(f"[green]Success[/green] - Deleted {counter} expired draft meldingen.")


@app.command()
def delete_expired_drafts() -> None:
    asyncio.run(delete_expired_draft_meldingen())


if __name__ == "__main__":
    app()
