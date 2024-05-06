from enum import StrEnum
from typing import Annotated, Generic, TypedDict, TypeVar

from fastapi import Depends, Query, Response

from meldingen.config import settings
from meldingen.models import BaseDBModel
from meldingen.repositories import BaseSQLAlchemyRepository


class PaginationParams(TypedDict):
    limit: int
    offset: int | None


def pagination_params(
    limit: Annotated[int, Query(title="The limit", ge=0)] = settings.default_page_size,
    offset: Annotated[int | None, Query(title="The offset of the page", ge=0)] = None,
) -> PaginationParams:
    return {"limit": limit, "offset": offset}


class SortingDirection(StrEnum):
    ASC = "ASC"
    DESC = "DESC"


class SortingParams(TypedDict):
    column: str
    direction: SortingDirection


def sort_param(sort: Annotated[tuple[str, SortingDirection], Query()] = ("id", SortingDirection.ASC)) -> SortingParams:
    return {"column": sort[0], "direction": sort[1]}


T = TypeVar("T", bound=BaseDBModel)
T_co = TypeVar("T_co", bound=BaseDBModel, covariant=True)


class ContentRangeHeaderAdder(Generic[T, T_co]):
    _repository: BaseSQLAlchemyRepository[T, T_co]
    _identifier: str

    def __init__(self, repository: BaseSQLAlchemyRepository[T, T_co], identifier: str) -> None:
        self._repository = repository
        self._identifier = identifier

    async def __call__(
        self,
        response: Response,
        pagination: Annotated[PaginationParams, Depends(pagination_params)],
    ) -> int:
        limit = pagination["limit"] or 0
        offset = pagination["offset"] or 0

        response.headers["Content-Range"] = (
            f"{self._identifier} {offset}-{limit - 1 + offset}/{await self._repository.count()}"
        )

        return 0
