from abc import ABCMeta
from typing import TypeVar

from meldingen_core.repositories import BaseMeldingRepository, BaseRepository
from sqlmodel import Session, select

from meldingen.models import Melding, User

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class BaseSQLModelRepository(BaseRepository[T, T_co], metaclass=ABCMeta):
    """Base repository for SQLModel based repositories."""

    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session


class MeldingRepository(BaseSQLModelRepository[Melding, Melding], BaseMeldingRepository):
    """Repository for Melding model."""

    def add(self, melding: Melding) -> None:
        self._session.add(melding)
        self._session.commit()
        self._session.refresh(melding)

    def list(self, *, limit: int | None = None, offset: int | None = None) -> list[Melding]:
        statement = select(Melding)

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = self._session.exec(statement)

        return list(results.all())

    def retrieve(self, pk: int) -> Melding | None:
        statement = select(Melding).where(Melding.id == pk)
        results = self._session.exec(statement)
        return results.one_or_none()


class UserRepository(BaseSQLModelRepository[User, User]):
    def add(self, user: User) -> None:
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)

    def list(self, *, limit: int | None = None, offset: int | None = None) -> list[User]:
        statement = select(User)

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = self._session.exec(statement)

        return list(results.all())

    def retrieve(self, pk: int) -> User | None:
        statement = select(User).where(User.id == pk)
        results = self._session.exec(statement)
        return results.one_or_none()

    def find_by_email(self, email: str) -> User:
        statement = select(User).where(User.email == email)
        results = self._session.exec(statement)

        return results.one()
