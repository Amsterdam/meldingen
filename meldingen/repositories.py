from meldingen_core.models import Melding
from meldingen_core.repositories import BaseMeldingRepository
from sqlmodel import Session


class BaseSQLModelRepository:
    """Base repository for SQLModel based repositories."""

    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session


class MeldingRepository(BaseSQLModelRepository, BaseMeldingRepository):
    """Repository for Melding model."""

    def add(self, melding: Melding) -> None:
        self._session.add(melding)
