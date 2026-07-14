from collections.abc import Sequence
from typing import override

from fastapi import HTTPException
from meldingen_core import SortingDirection
from meldingen_core.actions.note import NoteListAction as BaseNoteListAction
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from meldingen.models import Melding, Note
from meldingen.repositories import AttributeNotFoundException


class NoteListAction(BaseNoteListAction[Note, Melding]):
    @override
    async def __call__(
        self,
        melding_id: int,
        *,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Sequence[Note]:
        try:
            return await super().__call__(
                melding_id,
                sort_attribute_name=sort_attribute_name,
                sort_direction=sort_direction,
            )
        except AttributeNotFoundException as e:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_CONTENT,
                [{"loc": ("query", "sort"), "msg": e.message, "type": "attribute_not_found"}],
            )
