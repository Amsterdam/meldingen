import logging

from meldingen_core.classification import BaseClassifierAdapter
from openai import AsyncOpenAI

from meldingen.repositories import ClassificationRepository

logger = logging.getLogger(__name__)


class DummyClassifierAdapter(BaseClassifierAdapter):
    async def __call__(self, text: str) -> str:
        return text


class OpenAIClassifierAdapter(BaseClassifierAdapter):
    _client: AsyncOpenAI
    _model: str
    _classification_repository: ClassificationRepository

    def __init__(self, client: AsyncOpenAI, model: str, classification_repository: ClassificationRepository):
        self._client = client
        self._model = model
        self._classification_repository = classification_repository

    async def __call__(self, text: str) -> str | None:
        first = True
        classifications = ""
        for _classification in await self._classification_repository.list():
            if not first:
                classifications += ", "
            classifications += _classification.name
            first = False

        logger.debug(f"Classifications: {classifications}")

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a classifier of text. The following classifications exist: {classifications}.",
                },
                {
                    "role": "user",
                    "content": f"Please classify: {text}",
                },
            ],
        )

        classification = response.choices[0].message.content.strip()
        logger.debug(f"Classification according to LLM: {classification}")

        return classification
