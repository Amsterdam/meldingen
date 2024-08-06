from typing import Annotated, AsyncIterator

from fastapi import Depends
from meldingen_core.actions.classification import ClassificationDeleteAction
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.database import sessionmanager
from meldingen.repositories import ClassificationRepository


async def database_session() -> AsyncIterator[AsyncSession]:
    async with sessionmanager.session() as session:
        yield session


def classification_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> ClassificationRepository:
    return ClassificationRepository(session)


def classification_delete_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationDeleteAction:
    return ClassificationDeleteAction(repository)
