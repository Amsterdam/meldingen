from typing import Optional

from meldingen_core.models import Melding as BaseMelding
from sqlmodel import Field, SQLModel


class MeldingCreateInput(BaseMelding, SQLModel):
    ...


class Melding(BaseMelding, SQLModel, table=True):
    """SQLModel for Melding."""

    id: Optional[int] = Field(default=None, primary_key=True)
