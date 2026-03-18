import logging

from meldingen_core.classification import BaseClassifierAdapter
from pydantic_ai import Agent

from meldingen.classification import build_classification_prompt, build_dynamic_classification_response_model
from meldingen.repositories import ClassificationRepository

logger = logging.getLogger(__name__)


class AgentClassifierAdapter(BaseClassifierAdapter):
    _agent: Agent
    _repository: ClassificationRepository

    def __init__(self, agent: Agent, repository: ClassificationRepository):
        self._agent = agent
        self._repository = repository

    async def __call__(self, text: str) -> str | None:
        try:
            classification_prompt = await build_classification_prompt(self._repository)
            user_prompt = f"{classification_prompt}{text}"
            ClassificationModel = await build_dynamic_classification_response_model(self._repository)
            result = await self._agent.run(user_prompt, output_type=ClassificationModel)
            classification = getattr(result.output, "classification", None)

            print(f"Classification according to LLM: {classification}")
        except Exception as e:
            logger.error(f"Pydantic AI validation failed: {e}")

            print(f"Pydantic AI validation failed: {e}")
            return None
        return classification
