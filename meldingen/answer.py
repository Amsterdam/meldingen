from meldingen.repositories import AnswerRepository


class AnswerPurger:
    _repository: AnswerRepository

    def __init__(self, repository: AnswerRepository):
        self._repository = repository

    async def __call__(self, melding_id: int) -> None:
        answers = await self._repository.find_by_melding(melding_id)
        for answer in answers:
            await self._repository.delete(answer.id)