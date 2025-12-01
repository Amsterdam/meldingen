from collections.abc import Sequence
from typing import TypeVar

from fastapi import HTTPException
from meldingen_core import SortingDirection
from meldingen_core.actions.base import BaseListAction as BaseCoreListAction
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from meldingen.repositories import AttributeNotFoundException

T = TypeVar("T")


class BaseListAction(BaseCoreListAction[T]):
    async def __call__(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Sequence[T]:
        try:
            return await super().__call__(
                limit=limit, offset=offset, sort_attribute_name=sort_attribute_name, sort_direction=sort_direction
            )
        except AttributeNotFoundException as e:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_CONTENT,
                [{"loc": ("query", "sort"), "msg": e.message, "type": "attribute_not_found"}],
            )
