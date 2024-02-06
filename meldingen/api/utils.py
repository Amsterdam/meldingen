from typing import Annotated

from fastapi import Query

from meldingen.config import settings


def pagination_params(
    limit: Annotated[int, Query(title="The limit", ge=0)] = settings.default_page_size,
    offset: Annotated[int | None, Query(title="The offset of the page", ge=0)] = None,
) -> dict[str, int | None]:
    return {"limit": limit, "offset": offset}
