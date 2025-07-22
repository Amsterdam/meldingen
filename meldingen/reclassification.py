from meldingen_core.reclassification import BaseReclassification

from meldingen.answer import AnswerPurger
from meldingen.models import Classification, Melding


class Reclassifier(BaseReclassification[Melding, Classification]):
    _purge_answers: AnswerPurger

    def __init__(self, answer_purger: AnswerPurger):
        self._purge_answers = answer_purger

    async def __call__(self, melding: Melding, new_classification: Classification | None) -> None:
        old_classification = await melding.awaitable_attrs.classification
        if old_classification != new_classification:
            await self._purge_answers(melding.id)
