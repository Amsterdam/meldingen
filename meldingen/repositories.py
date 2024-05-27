from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from typing import Any, TypeVar

from meldingen_core import SortingDirection
from meldingen_core.exceptions import NotFoundException
from meldingen_core.repositories import (
    BaseAnswerRepository,
    BaseClassificationRepository,
    BaseFormRepository,
    BaseMeldingRepository,
    BaseQuestionRepository,
    BaseRepository,
    BaseUserRepository,
)
from sqlalchemy import Select, desc, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Relationship
from sqlalchemy.sql import func

from meldingen.models import Answer, BaseDBModel, Classification, Form, Group, Melding, Question, User


class AttributeNotFoundException(Exception):
    message: str

    def __init__(self, message: str):
        self.message = message


T = TypeVar("T", bound=BaseDBModel)
T_co = TypeVar("T_co", bound=BaseDBModel, covariant=True)


class BaseSQLAlchemyRepository(BaseRepository[T, T_co], metaclass=ABCMeta):
    """Base repository for SqlAlchemy based repositories."""

    _session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    def get_model_type(self) -> type[Any]: ...

    async def save(self, model: T, *, commit: bool = True) -> None:
        self._session.add(model)

        if commit:
            try:
                await self._session.commit()
            except IntegrityError as integrity_error:
                await self._session.rollback()
                raise integrity_error
            else:
                await self._session.refresh(model)

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Collection[T_co]:
        _type = self.get_model_type()
        statement = select(_type)

        statement = self._handle_sorting(_type, statement, sort_attribute_name, sort_direction)

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = await self._session.execute(statement)

        return results.scalars().unique().all()

    async def retrieve(self, pk: int) -> T | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.id == pk)
        results = await self._session.execute(statement)
        return results.scalars().unique().one_or_none()

    async def delete(self, pk: int) -> None:
        db_item = await self.retrieve(pk=pk)
        if db_item is None:
            raise NotFoundException()

        await self._session.delete(db_item)
        await self._session.commit()

    async def count(self) -> int:
        _type = self.get_model_type()
        statement = select(func.count(_type.id))
        result = await self._session.execute(statement)

        return result.scalars().one()

    def _handle_sorting(
        self,
        _type: type[Any],
        statement: Select[Any],
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Select[Any]:
        if sort_attribute_name is not None:
            sort_attribute = _type.__mapper__.attrs.get(sort_attribute_name)

            if sort_attribute is None:
                raise AttributeNotFoundException(f"Attribute {sort_attribute_name} not found")

            if isinstance(sort_attribute, Relationship):
                raise AttributeNotFoundException(f"Cannot sort on relationship {sort_attribute_name}")

            if sort_direction is None or sort_direction == SortingDirection.ASC:
                statement = statement.order_by(sort_attribute)
            elif sort_direction == SortingDirection.DESC:
                statement = statement.order_by(desc(sort_attribute))

        return statement


class MeldingRepository(BaseSQLAlchemyRepository[Melding, Melding], BaseMeldingRepository[Melding, Melding]):
    """Repository for Melding model."""

    def get_model_type(self) -> type[Melding]:
        return Melding


class UserRepository(BaseSQLAlchemyRepository[User, User], BaseUserRepository):
    def get_model_type(self) -> type[User]:
        return User

    async def find_by_email(self, email: str) -> User:
        statement = select(User).where(User.email == email)

        results = await self._session.execute(statement)

        return results.scalars().unique().one()


class GroupRepository(BaseSQLAlchemyRepository[Group, Group]):
    def get_model_type(self) -> type[Group]:
        return Group

    async def find_by_name(self, name: str) -> Group:
        statement = select(Group).where(Group.name == name)
        results = await self._session.execute(statement)

        return results.scalars().one()


class ClassificationRepository(BaseSQLAlchemyRepository[Classification, Classification], BaseClassificationRepository):
    def get_model_type(self) -> type[Classification]:
        return Classification

    async def find_by_name(self, name: str) -> Classification:
        statement = select(Classification).where(Classification.name == name)
        result = await self._session.execute(statement)
        classification = result.scalars().one_or_none()

        if classification is None:
            raise NotFoundException()

        return classification


class FormRepository(BaseSQLAlchemyRepository[Form, Form], BaseFormRepository):
    def get_model_type(self) -> type[Form]:
        return Form

    async def find_by_classification_id(self, classification_id: int) -> Form:
        _type = self.get_model_type()
        statement = select(_type).where(_type.classification_id == classification_id)

        result = await self._session.execute(statement)
        try:
            return result.scalars().one()
        except NoResultFound:
            raise NotFoundException()


class QuestionRepository(BaseSQLAlchemyRepository[Question, Question], BaseQuestionRepository):
    def get_model_type(self) -> type[Question]:
        return Question

    async def retrieve_by_text_and_form_id(self, text: str, form_id: int) -> Question | None:
        _type = self.get_model_type()
        statement = (
            select(_type).where(_type.form_id == form_id).where(_type.text == text).order_by(desc(_type.id)).limit(1)
        )
        results = await self._session.execute(statement)

        return results.scalars().one_or_none()


class AnswerRepository(BaseSQLAlchemyRepository[Answer, Answer], BaseAnswerRepository):
    def get_model_type(self) -> type[Answer]:
        return Answer
