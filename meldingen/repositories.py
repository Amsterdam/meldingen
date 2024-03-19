from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from typing import Any, TypeVar, override

from meldingen_core.exceptions import NotFoundException
from meldingen_core.repositories import (
    BaseClassificationRepository,
    BaseMeldingRepository,
    BaseRepository,
    BaseUserRepository,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.models import BaseDBModel, Classification, FormIoComponent, FormIoForm, Group, Melding, User

T = TypeVar("T", bound=BaseDBModel)
T_co = TypeVar("T_co", bound=BaseDBModel, covariant=True)


class BaseSQLAlchemyRepository(BaseRepository[T, T_co], metaclass=ABCMeta):
    """Base repository for SqlAlchemy based repositories."""

    _session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    def get_model_type(self) -> type[Any]: ...

    @override
    async def save(self, model: T) -> None:
        self._session.add(model)

        try:
            await self._session.commit()
        except IntegrityError as integrity_error:
            await self._session.rollback()
            raise integrity_error
        else:
            await self._session.refresh(model)

    @override
    async def list(self, *, limit: int | None = None, offset: int | None = None) -> Collection[T_co]:
        statement = select(self.get_model_type())

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = await self._session.execute(statement)

        return results.scalars().unique().all()

    @override
    async def retrieve(self, pk: int) -> T | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.id == pk)
        results = await self._session.execute(statement)
        return results.scalars().unique().one_or_none()

    @override
    async def delete(self, pk: int) -> None:
        db_item = await self.retrieve(pk=pk)
        if db_item is None:
            raise NotFoundException()

        await self._session.delete(db_item)
        await self._session.commit()


class MeldingRepository(BaseSQLAlchemyRepository[Melding, Melding], BaseMeldingRepository[Melding, Melding]):
    """Repository for Melding model."""

    @override
    def get_model_type(self) -> type[Melding]:
        return Melding


class UserRepository(BaseSQLAlchemyRepository[User, User], BaseUserRepository):
    @override
    def get_model_type(self) -> type[User]:
        return User

    async def find_by_email(self, email: str) -> User:
        statement = select(User).where(User.email == email)

        results = await self._session.execute(statement)

        return results.scalars().unique().one()


class GroupRepository(BaseSQLAlchemyRepository[Group, Group]):
    @override
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


class FormIoFormRepository(BaseSQLAlchemyRepository[FormIoForm, FormIoForm]):
    @override
    def get_model_type(self) -> type[FormIoForm]:
        return FormIoForm

    async def retrieve_primary_form(self) -> FormIoForm | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.is_primary == True)
        results = await self._session.execute(statement)
        return results.scalars().one_or_none()

    async def delete_components(self, pk: int) -> None:
        statement = delete(FormIoComponent).where(FormIoComponent.form_id == pk)
        await self._session.execute(statement)


class FormIoComponentRepository(BaseSQLAlchemyRepository[FormIoComponent, FormIoComponent]):
    @override
    def get_model_type(self) -> type[FormIoComponent]:
        return FormIoComponent
