from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from typing import TypeVar, override

from meldingen_core.repositories import BaseMeldingRepository, BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from meldingen.models import BaseDBModel, Melding, User

T = TypeVar("T", bound=BaseDBModel)
T_co = TypeVar("T_co", bound=BaseDBModel, covariant=True)


class BaseSQLModelRepository(BaseRepository[T, T_co], metaclass=ABCMeta):
    """Base repository for SQLModel based repositories."""

    _session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    def get_model_type(self) -> type[T_co]: ...

    @override
    async def add(self, model: T) -> None:
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)

    @override
    async def list(self, *, limit: int | None = None, offset: int | None = None) -> Collection[T_co]:
        statement = select(self.get_model_type())

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = await self._session.execute(statement)

        return results.scalars().all()

    @override
    async def retrieve(self, pk: int) -> T_co | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.id == pk)
        results = await self._session.execute(statement)
        return results.scalars().one_or_none()


class MeldingRepository(BaseSQLModelRepository[Melding, Melding], BaseMeldingRepository):
    """Repository for Melding model."""

    @override
    def get_model_type(self) -> type[Melding]:
        return Melding


class UserRepository(BaseSQLModelRepository[User, User]):
    @override
    def get_model_type(self) -> type[User]:
        return User

    async def find_by_email(self, email: str) -> User:
        statement = select(User).where(User.email == email)
        results = await self._session.execute(statement)

        return results.scalars().one()

    def delete(self, pk: int) -> None:
        db_user = self.retrieve(pk=pk)
        self._session.delete(db_user)
