from pytest_bdd import given, parsers
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.config import settings
from meldingen.models import Classification
from tests.scenarios.conftest import async_step


@given(parsers.parse('there is a classification with the name: "{name}"'), target_fixture="classification")
@async_step
async def there_is_a_classification(name: str, db_session: AsyncSession) -> Classification:
    classification = Classification(name=name)

    db_session.add(classification)
    await db_session.commit()

    return classification


@given(parsers.parse("there is a default classification"), target_fixture="default_classification")
@async_step
async def there_is_a_default_classification(db_session: AsyncSession) -> Classification:
    classification = Classification(name=settings.llm_fallback_classification_name)

    db_session.add(classification)
    await db_session.commit()

    return classification
