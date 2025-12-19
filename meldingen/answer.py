from meldingen.models import Melding
from meldingen.repositories import AnswerRepository, MeldingRepository


class AnswerPurger:
    _repository: MeldingRepository

    def __init__(self, repository: MeldingRepository) -> None:
        self._repository = repository

    async def __call__(self, melding: Melding) -> None:
        answers = await melding.awaitable_attrs.answers

        answers.clear()
        await self._repository.save(melding)
