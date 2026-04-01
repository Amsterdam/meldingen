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

            logger.info(f"Classification according to LLM: {classification}")
            print(f"Classification according to LLM: {classification}")
        except Exception as e:
            # Print the full exception cause chain to find root cause (SSL errors, DNS, etc.)
            print("=" * 60)
            print("LLM CLASSIFICATION ERROR DEBUG")
            print("=" * 60)
            cause: BaseException = e
            depth = 0
            while cause is not None:
                print(f"[{depth}] {type(cause).__module__}.{type(cause).__name__}: {cause}")
                print(f"    args: {cause.args}")
                cause = cause.__cause__
                depth += 1
            print("=" * 60)

            import traceback

            traceback.print_exc()
            return None
        return classification
