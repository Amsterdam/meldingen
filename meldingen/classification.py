import logging
from meldingen_core.classification import BaseClassifierAdapter
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import Literal

from meldingen.repositories import ClassificationRepository

logger = logging.getLogger(__name__)


class DummyClassifierAdapter(BaseClassifierAdapter):
    async def __call__(self, text: str) -> str:
        return text


class ClassificationResponse(BaseModel):
    classification: str = Field(..., description="The chosen classification")


async def build_classification_model(repository: ClassificationRepository) -> type[BaseModel]:
    classifications_list = [c.name for c in await repository.list()]
    annotations = {"classification": Literal[tuple(classifications_list)]}
    namespace = {"__annotations__": annotations, "classification": Field(..., description="The chosen classification")}
    return type("ClassificationResponse", (BaseModel,), namespace)


class OpenAIClassifierAdapter(BaseClassifierAdapter):
    _agent: Agent
    _repository: ClassificationRepository

    def __init__(self, agent: Agent, repository: ClassificationRepository):
        self._agent = agent
        self._repository = repository

    async def __call__(self, text: str) -> str | None:
        user_prompt = f"Please classify: {text}"
        try:
            ClassificationModel = await build_classification_model(self._repository)
            result = await self._agent.run(user_prompt, output_type=ClassificationModel)
            classification = result.output.classification

            print(f"Classification according to LLM: {classification}")
        except Exception as e:
            logger.error(f"Pydantic AI validation failed: {e}")

            print(f"Pydantic AI validation failed: {e}")
            return None
        return classification
