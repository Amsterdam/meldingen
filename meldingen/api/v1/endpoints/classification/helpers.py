from typing import Annotated

from fastapi import Depends

from meldingen.api.utils import ContentRangeHeaderAdder
from meldingen.dependencies import classification_repository
from meldingen.models import Classification
from meldingen.repositories import ClassificationRepository


async def content_range_header_adder(
    repo: Annotated[ClassificationRepository, Depends(classification_repository)],
) -> ContentRangeHeaderAdder[Classification]:
    return ContentRangeHeaderAdder(repo, "classification")
