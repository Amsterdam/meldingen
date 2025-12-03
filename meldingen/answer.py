from meldingen.models import Answer, AnswerTypeEnum
from meldingen.repositories import AnswerRepository
from meldingen.schemas.input import AnswerInputUnion


class AnswerPurger:
    _repository: AnswerRepository

    def __init__(self, repository: AnswerRepository):
        self._repository = repository

    async def __call__(self, melding_id: int) -> None:
        answers = await self._repository.find_by_melding(melding_id)
        for answer in answers:
            await self._repository.delete(answer.id)


class AnswerUpdateResolver:
    """Resolves which fields to update based on the answer type."""

    async def __call__(self, answer: Answer, answer_input: AnswerInputUnion) -> Answer:
        match answer_input.type:
            case AnswerTypeEnum.text:
                answer.text = answer_input.text
            case AnswerTypeEnum.time:
                answer.time = answer_input.time
            case _:
                raise Exception(f"Unsupported answer type: {answer_input.type}")

        return answer
