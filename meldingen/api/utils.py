from dataclasses import dataclass
from typing import Annotated, AsyncIterator, Generic, List, TypedDict, TypeVar

from fastapi import Depends, HTTPException, Query, Response, UploadFile
from meldingen_core import SortingDirection
from pydantic import BaseModel, RootModel, ValidationError
from sqlalchemy import ColumnExpressionArgument
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

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

        raise HTTPException(HTTP_422_UNPROCESSABLE_CONTENT, errors)


def optional_sort_param(sort: Annotated[str | None, Query()] = None) -> SortParams | None:
    """Like ``sort_param`` but optional, so the caller can fall back to its own default ordering."""
    return None if sort is None else sort_param(sort)


class FilterParams(BaseModel, extra="ignore"):
    q: str | None = None


def filter_param(filter: Annotated[str | None, Query()] = None) -> FilterParams:
    if filter is None:
        return FilterParams()

    try:
        return FilterParams.model_validate_json(filter)
    except ValidationError as e:
        errors = e.errors()
        for error in errors:
            error["loc"] = ("query", "filter")

        raise HTTPException(HTTP_422_UNPROCESSABLE_CONTENT, errors)


T = TypeVar("T", bound=BaseDBModel)


@dataclass(frozen=True)
class PreparedAttachmentUpload:
    filename: str
    content_type: str
    data_header: bytes
    iterator: AsyncIterator[bytes]

    @classmethod
    async def from_upload_file(
        cls,
        file: UploadFile,
        data_header_size: int = 2048,
        chunk_size: int = 1024 * 1024,
    ) -> "PreparedAttachmentUpload":
        # When uploading a file without filename, Starlette gives us a string instead of an instance
        # of UploadFile, so actually the filename will always be available. To satisfy the type
        # checker we assert that is the case.
        assert file.filename is not None
        assert file.content_type is not None

        data_header = await file.read(data_header_size)
        await file.seek(0)

        async def iterate() -> AsyncIterator[bytes]:
            while chunk := await file.read(chunk_size):
                yield chunk

        return cls(
            filename=file.filename,
            content_type=file.content_type,
            data_header=data_header,
            iterator=iterate(),
        )


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
        filters: List[ColumnExpressionArgument[bool]] | None = None,
    ) -> int:
        limit = pagination["limit"] or 0
        offset = pagination["offset"] or 0

        response.headers["Content-Range"] = (
            f"{self._identifier} {offset}-{limit - 1 + offset}/{await self._repository.count(filters)}"
        )

        return 0
