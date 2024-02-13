from typing import Optional

from meldingen_core.models import Melding as BaseMelding
from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class BaseDBModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)


class MeldingCreateInput(BaseMelding, SQLModel): ...


class Melding(BaseMelding, BaseDBModel, table=True):
    """SQLModel for Melding."""

    id: Optional[int] = Field(default=None, primary_key=True)


class UserInput(SQLModel):
    username: str
    email: EmailStr


class User(BaseDBModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(min_length=1, max_length=320, unique=True)
    email: str = Field(min_length=5, max_length=320, unique=True)
