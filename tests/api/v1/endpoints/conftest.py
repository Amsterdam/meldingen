# from datetime import datetime, timedelta
from typing import Annotated

import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends
from meldingen_core.exceptions import NotFoundException
# from pydantic import TypeAdapter
from pytest import FixtureRequest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from meldingen.authentication import authenticate_user
from meldingen.containers import classification_repository, get_database_session
# from meldingen.containers import Container
from meldingen.models import (
    Classification,
    # Form,
    # FormIoComponent,
    # FormIoComponentTypeEnum,
    # FormIoFormDisplayEnum,
    # Melding,
    # Question,
    # StaticForm,
    # StaticFormTypeEnum,
    User,
)
from meldingen.repositories import (
    ClassificationRepository,
    # FormRepository,
    # MeldingRepository,
    # QuestionRepository,
    # StaticFormRepository,
)


# @pytest_asyncio.fixture
# async def melding_repository(container: Container) -> MeldingRepository:
#     return await container.melding_repository()
#
#
# @pytest.fixture
# def melding_text(request: FixtureRequest) -> str:
#     """Fixture providing a test melding text."""
#
#     if hasattr(request, "param"):
#         return str(request.param)
#     else:
#         return "This is a test melding."
#
#
# @pytest.fixture
# def melding_state(request: FixtureRequest) -> str | None:
#     if hasattr(request, "param"):
#         return str(request.param)
#     else:
#         return None
#
#
# @pytest.fixture
# def melding_token(request: FixtureRequest) -> str | None:
#     if hasattr(request, "param"):
#         return str(request.param)
#
#     return None
#
#
# @pytest.fixture
# def melding_token_expires(request: FixtureRequest) -> datetime | None:
#     if hasattr(request, "param"):
#         timedelta_adapter = TypeAdapter(timedelta)
#         return datetime.now() - timedelta_adapter.validate_python(request.param)
#
#     return None
#
#
# @pytest_asyncio.fixture
# async def test_melding(
#     melding_repository: MeldingRepository,
#     melding_text: str,
#     melding_state: str | None,
#     melding_token: str | None,
#     melding_token_expires: datetime | None,
# ) -> Melding:
#     """Fixture providing a single test melding instance."""
#
#     melding = Melding(text=melding_text)
#     if melding_state is not None:
#         melding.state = melding_state
#
#     if melding_token is not None:
#         melding.token = melding_token
#
#     if melding_token_expires is not None:
#         melding.token_expires = melding_token_expires
#
#     await melding_repository.save(melding)
#
#     return melding
#
#
# @pytest_asyncio.fixture
# async def test_melding_with_classification(
#     melding_repository: MeldingRepository,
#     test_melding: Melding,
#     classification: Classification,
# ) -> Melding:
#     test_melding.classification = classification
#
#     await melding_repository.save(test_melding)
#
#     return test_melding
#
#
# @pytest_asyncio.fixture
# async def test_meldingen(melding_repository: MeldingRepository, melding_text: str) -> list[Melding]:
#     """Fixture providing a list test melding instances."""
#
#     meldingen = []
#     for i in range(10):
#         melding = Melding(text=f"{melding_text} {i}")
#
#         await melding_repository.save(melding)
#
#         meldingen.append(melding)
#
#     return meldingen
#
#
async def authenticate_user_override(token: str | None = None) -> User:
    user = User(username="user@example.com", email="user@example.com")
    user.id = 400
    return user


@pytest.fixture(scope="session")
def auth_user(app: FastAPI) -> None:
    app.dependency_overrides[authenticate_user] = authenticate_user_override


@pytest_asyncio.fixture(scope="session")
async def database_session(database_engine: AsyncEngine) -> AsyncSession:
    async_session = async_sessionmaker(database_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture(scope="session")
def classification_repo(database_session: AsyncSession) -> ClassificationRepository:
    return ClassificationRepository(database_session)


@pytest.fixture(scope="session")
def classification_name(request: FixtureRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "classification name"


@pytest_asyncio.fixture(scope="session")
async def classification(classification_name: str, classification_repo: ClassificationRepository) -> Classification:
    try:
        classification = await classification_repo.find_by_name(classification_name)
    except NotFoundException:
        classification = Classification(name=classification_name)
        await classification_repo.save(classification)

    return classification


# @pytest_asyncio.fixture
# async def classifications(classification_repository: ClassificationRepository) -> list[Classification]:
#     classifications = []
#     for n in range(10):
#         classification = Classification(f"category: {n}")
#         await classification_repository.save(classification)
#         classifications.append(classification)
#
#     return classifications
#
#
# @pytest_asyncio.fixture
# async def classification_with_form(
#     classification_repository: ClassificationRepository, form_repository: FormRepository
# ) -> Classification:
#     classification = Classification("test_classification")
#     await classification_repository.save(classification)
#     form = Form(title="test_form", display=FormIoFormDisplayEnum.form, classification=classification)
#     await form_repository.save(form)
#
#     return classification
#
#
# @pytest_asyncio.fixture
# async def form_repository(container: Container) -> FormRepository:
#     return await container.form_repository()
#
#
# @pytest_asyncio.fixture
# async def static_form_repository(container: Container) -> StaticFormRepository:
#     return await container.static_form_repository()
#
#
# @pytest_asyncio.fixture
# async def question_repository(container: Container) -> QuestionRepository:
#     return await container.question_repository()
#
#
# @pytest.fixture
# def form_title(request: FixtureRequest) -> str:
#     if hasattr(request, "param"):
#         return str(request.param)
#     else:
#         return "Form"
#
#
# @pytest_asyncio.fixture
# async def form(form_repository: FormRepository, question_repository: QuestionRepository, form_title: str) -> Form:
#     form = Form(title=form_title, display=FormIoFormDisplayEnum.form)
#
#     component = FormIoComponent(
#         label="Wat is uw klacht?",
#         description="",
#         key="wat-is-uw_klacht",
#         type=FormIoComponentTypeEnum.text_area,
#         input=True,
#         auto_expand=True,
#         show_char_count=True,
#     )
#
#     components = await form.awaitable_attrs.components
#     components.append(component)
#
#     await form_repository.save(form)
#
#     question = Question(text=component.description, form=form)
#
#     await question_repository.save(question)
#
#     component.question = question
#
#     await form_repository.save(form)
#
#     return form
#
#
# @pytest_asyncio.fixture
# async def form_with_classification(
#     classification_repository: ClassificationRepository,
#     form_repository: FormRepository,
#     question_repository: QuestionRepository,
#     form_title: str,
# ) -> Form:
#     form = Form(title=form_title, display=FormIoFormDisplayEnum.form)
#
#     component = FormIoComponent(
#         label="Wat is uw klacht?",
#         description="",
#         key="wat-is-uw_klacht",
#         type=FormIoComponentTypeEnum.text_area,
#         input=True,
#         auto_expand=True,
#         show_char_count=True,
#     )
#
#     components = await form.awaitable_attrs.components
#     components.append(component)
#
#     await form_repository.save(form)
#
#     question = Question(text=component.description, form=form)
#
#     await question_repository.save(question)
#
#     component.question = question
#
#     try:
#         classification = await classification_repository.find_by_name("test_classification")
#     except NotFoundException:
#         classification = Classification("test_classification")
#         await classification_repository.save(classification)
#
#     form.classification = classification
#     await form_repository.save(form)
#
#     return form
#
#
# @pytest_asyncio.fixture
# async def test_forms(form_repository: FormRepository) -> list[Form]:
#     forms = []
#     for n in range(1, 11):
#         form = Form(title=f"Form #{n}", display=FormIoFormDisplayEnum.form)
#
#         await form_repository.save(form)
#
#         forms.append(form)
#
#     return forms
#
#
# @pytest_asyncio.fixture
# async def primary_form(static_form_repository: StaticFormRepository) -> StaticForm:
#     try:
#         primary_form = await static_form_repository.retrieve_by_type(StaticFormTypeEnum.primary)
#     except NotFoundException:
#         primary_form = StaticForm(
#             type=StaticFormTypeEnum.primary, title="Primary form", display=FormIoFormDisplayEnum.form
#         )
#
#         component = FormIoComponent(
#             label="Waar gaat het om?",
#             description="",
#             key="waar-gaat-het-om",
#             type=FormIoComponentTypeEnum.text_area,
#             input=True,
#             auto_expand=False,
#             show_char_count=True,
#         )
#
#         components = await primary_form.awaitable_attrs.components
#         components.append(component)
#
#         await static_form_repository.save(primary_form)
#
#     return primary_form
