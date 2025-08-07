import logging

from meldingen_core.classification import BaseClassifierAdapter
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class DummyClassifierAdapter(BaseClassifierAdapter):
    async def __call__(self, text: str) -> str:
        return text


class OpenAIClassifierAdapter(BaseClassifierAdapter):
    _client: AsyncOpenAI
    _model: str

    def __init__(self, client: AsyncOpenAI, model: str):
        self._client = client
        self._model = model

    async def __call__(self, text: str) -> str | None:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a classifier of text. The following classifications exist: trees, roads, street lights, car parking.",
                },
                {
                    "role": "user",
                    "content": f"Please classify: {text}",
                },
            ],
        )

        classification = response.choices[0].message.content
        logger.debug(f"Classification according to LLM: {classification}")

        return classification
