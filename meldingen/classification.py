from meldingen_core.classification import BaseClassifierAdapter
from meldingen_core.reclassification import BaseReclassification

from meldingen.models import Classification, Melding
from meldingen.repositories import AnswerRepository


class DummyClassifierAdapter(BaseClassifierAdapter):
    async def __call__(self, text: str) -> str:
        return text


class AnswerPurger:
    _repository: AnswerRepository

    def __init__(self, repository: AnswerRepository):
        self._repository = repository

    async def __call__(self, melding_id: int) -> None:
        answers = await self._repository.find_by_melding(melding_id)
        for answer in answers:
            await self._repository.delete(answer.id)


class Reclassifier(BaseReclassification[Melding, Classification]):
    _purge_answers: AnswerPurger

    def __init__(self, answer_purger: AnswerPurger):
        self._purge_answers = answer_purger

    async def __call__(self, melding: Melding, new_classification: Classification | None) -> None: ...
