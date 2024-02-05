from meldingen_core.models import Melding as BaseMelding
from meldingen_core.repositories import BaseRepository, BaseMeldingRepository
from sqlmodel import Session, select
from typing import TypeVar

from meldingen.models import Melding

T = TypeVar('T')
T_co = TypeVar("T_co", covariant=True)


class BaseSQLModelRepository(BaseRepository[T, T_co]):
    """Base repository for SQLModel based repositories."""

    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session


class MeldingRepository(BaseSQLModelRepository[Melding, Melding], BaseMeldingRepository):
    """Repository for Melding model."""

    def add(self, melding: BaseMelding) -> None:
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
