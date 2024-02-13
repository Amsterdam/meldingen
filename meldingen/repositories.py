from abc import ABCMeta, abstractmethod
from typing import TypeVar

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

    async def add(self, model: T) -> None:
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)

    async def list(self, *, limit: int | None = None, offset: int | None = None) -> list[T_co]:
        statement = select(self.get_model_type())

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = await self._session.execute(statement)

        return list(results.all())

    async def retrieve(self, pk: int) -> T_co | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.id == pk)
        results = await self._session.execute(statement)
        return results.one_or_none()


class MeldingRepository(BaseSQLModelRepository[Melding, Melding], BaseMeldingRepository):
    """Repository for Melding model."""

    def get_model_type(self) -> type[Melding]:
        return Melding


class UserRepository(BaseSQLModelRepository[User, User]):
    def get_model_type(self) -> type[User]:
        return User

    async def find_by_email(self, email: str) -> User:
        statement = select(User).where(User.email == email)
        results = await self._session.execute(statement)

        return results.one()
