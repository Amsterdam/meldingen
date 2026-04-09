import logging
from typing import Literal

from pydantic import BaseModel, Field, create_model

from meldingen.repositories import ClassificationRepository

logger = logging.getLogger(__name__)


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
