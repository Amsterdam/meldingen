import logging
from typing import Literal

from pydantic import BaseModel, Field, create_model

from meldingen.repositories import ClassificationRepository

logger = logging.getLogger(__name__)


CLASSIFICATION_SYSTEM_PROMPT = (
    "Je bent een expert classificeerder van meldingen over de openbare ruimte in de gemeente Amsterdam.\n\n"
    "Regels:\n"
    "1. Je krijgt een lijst classificaties, elk met een instructie die beschrijft wanneer deze classificatie van toepassing is.\n"
    "2. Je krijgt een meldtekst van een burger.\n"
    "3. Vergelijk de meldtekst met ELKE classificatie-instructie en bepaal welke het beste past.\n"
    "4. Als meerdere classificaties deels van toepassing lijken, kies dan de classificatie "
    "waarvan de instructie het meest specifiek overeenkomt met het hoofdonderwerp van de melding.\n"
)


def get_classification_system_prompt() -> str:
    return CLASSIFICATION_SYSTEM_PROMPT


class ClassificationResponse(BaseModel):
    classification: str = Field(..., description="The chosen classification")


async def build_dynamic_classification_response_model(repository: ClassificationRepository) -> type[BaseModel]:
    """Function to create a dynamic Pydantic model to ensure the LLM's response is one of the valid classification names inside the Literal tuple."""

    classifications_list = [c.name for c in await repository.list()]
    classification_type = Literal[tuple(classifications_list)]
    return create_model(
        "ClassificationResponse",
        classification=(classification_type, Field(..., description="The chosen classification")),
    )


async def build_classification_prompt(repository: ClassificationRepository) -> str:
    """Build a prompt section listing all classifications with their instructions."""

    classifications = await repository.list()
    lines = [f"- **{c.name}**: {c.instructions}" if c.instructions else f"- **{c.name}**" for c in classifications]

    return "Beschikbare classificaties:\n" + "\n".join(lines) + "\n\n" + "Meldtekst:\n"
