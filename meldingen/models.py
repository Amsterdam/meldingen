from typing import Optional

from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import User as BaseUser
from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class BaseDBModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)


class MeldingCreateInput(BaseMelding, SQLModel): ...


class Melding(BaseMelding, BaseDBModel, table=True):
    """SQLModel for Melding."""


class UserCreateInput(BaseUser, SQLModel):
    email: EmailStr


class User(BaseUser, BaseDBModel, table=True):
    username: str = Field(min_length=1, max_length=320, unique=True)
    email: str = Field(min_length=5, max_length=320, unique=True)
