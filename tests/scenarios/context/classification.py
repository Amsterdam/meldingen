from typing import AsyncIterator

from pytest_bdd import given, parsers
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.models import Classification
from tests.scenarios.conftest import async_to_sync


@given(parsers.parse("there is a classification {name:l}"))
@async_to_sync
async def there_is_a_classification(name: str, db_session: AsyncIterator[AsyncSession]) -> Classification:
    classification = Classification(name=name)

    db_session.add(classification)
    await db_session.commit()

    return classification
