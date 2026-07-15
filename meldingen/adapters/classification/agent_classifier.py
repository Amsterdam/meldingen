import logging

from meldingen_core.classification import BaseClassifierAdapter
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.output import NativeOutput, PromptedOutput
from pydantic_ai.settings import ModelSettings

from meldingen.classification import build_classification_prompt, build_dynamic_classification_response_model
from meldingen.repositories import ClassificationRepository

logger = logging.getLogger(__name__)


class AgentClassifierAdapter(BaseClassifierAdapter):
    _agent: Agent
    _repository: ClassificationRepository
    _model_settings: ModelSettings | None

    def __init__(
        self,
        agent: Agent,
        repository: ClassificationRepository,
        model_settings: ModelSettings | None = None,
    ):
        self._agent = agent
        self._repository = repository
        self._model_settings = model_settings

    async def classify(self, text: str) -> str | None:
        """Run the LLM and return the chosen classification name.

        Raises any exception from the LLM call, prompt building, or response
        validation. Use this method directly when you need errors to surface
        (tests, eval suites); the production entrypoint is `__call__`, which
        wraps this in a try/except so a misbehaving LLM never blocks melding
        creation.

        Output mode: we prefer `NativeOutput`, which sends the JSON schema via
        the OpenAI `response_format: {type: "json_schema"}` request parameter
        instead of the default `ToolOutput` (tool/function calling) or
        `PromptedOutput` (extra prompt-injected instructions).

        - `ToolOutput` requires the model to emit a structured tool call, which
          small open-weight models (e.g. Gemma 3 1B on Docker Model Runner)
          cannot reliably produce.
        - `PromptedOutput` adds instruction messages to the conversation, which
          breaks chat templates that require strict user/assistant alternation
          (Gemma rejects this with "Conversation roles must alternate").
        - `NativeOutput` leaves the [system, user] message shape untouched and
          relies on the server-side response_format parameter, which llama.cpp
          and OpenAI both honor.

        Not every model supports native structured output (e.g. the Azure
        provider's profile for Mistral models); pydantic-ai refuses to even
        attempt `NativeOutput` for those, so we fall back to `PromptedOutput`
        based on the model's profile.
        """
        classification_prompt = await build_classification_prompt(self._repository)
        user_prompt = f"{classification_prompt}{text}"
        ClassificationModel = await build_dynamic_classification_response_model(self._repository)

        model = self._agent.model
        use_native = isinstance(model, Model) and model.profile.supports_json_schema_output
        output_type = NativeOutput(ClassificationModel) if use_native else PromptedOutput(ClassificationModel)

        result = await self._agent.run(user_prompt, output_type=output_type, model_settings=self._model_settings)
        classification = getattr(result.output, "classification", None)

        logger.info("LLM classified melding as %r", classification)
        return classification

    async def __call__(self, text: str) -> str | None:
        try:
            return await self.classify(text)
        except Exception:
            logger.exception("LLM classification failed")
            return None
