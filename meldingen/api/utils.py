from typing import Annotated, Generic, TypedDict, TypeVar, AsyncIterator

from fastapi import Depends, HTTPException, Query, Response
from httpx import AsyncClient
from meldingen_core import SortingDirection
from pydantic import RootModel, ValidationError
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

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


class SortParams(RootModel[tuple[str, SortingDirection]]):
    root: tuple[str, SortingDirection]

    def get_attribute_name(self) -> str:
        return self.root[0]

    def get_direction(self) -> SortingDirection:
        return self.root[1]


def sort_param(sort: Annotated[str, Query()] = f'["id","{SortingDirection.ASC}"]') -> SortParams:
    try:
        return SortParams.model_validate_json(sort)
    except ValidationError as e:
        errors = e.errors()
        for error in errors:
            error["loc"] = ("query", "sort")

        raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, errors)


T = TypeVar("T", bound=BaseDBModel)


class ContentRangeHeaderAdder(Generic[T]):
    _repository: BaseSQLAlchemyRepository[T]
    _identifier: str

    def __init__(self, repository: BaseSQLAlchemyRepository[T], identifier: str) -> None:
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


async def stream_data_from_url(url: str) -> AsyncIterator[bytes]:
    async with AsyncClient() as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            async for chunk in response.aiter_bytes():
                yield chunk