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
            logger.error(f"LLM classification failed: {e}", exc_info=True)

            # Walk the exception chain to find the root cause (SSL details, DNS errors, etc.)
            cause: BaseException = e
            chain = [f"{type(cause).__name__}: {cause}"]
            while cause.__cause__ is not None:
                cause = cause.__cause__
                chain.append(f"{type(cause).__module__}.{type(cause).__name__}: {cause}")
            logger.error(f"LLM error chain: {' -> '.join(chain)}")

            # Log underlying connection details if available
            if hasattr(e, "request"):
                logger.error(f"LLM request URL: {e.request.url}")  # type: ignore[union-attr]

            import traceback

            traceback.print_exc()
            return None
        return classification
