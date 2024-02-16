from typing import Optional

from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import User as BaseUser
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


class BaseDBModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)


class MeldingCreateInput(BaseMelding, SQLModel): ...


class Melding(BaseMelding, BaseDBModel, table=True):
    """SQLModel for Melding."""


class UserInput(BaseUser, SQLModel):
    email: EmailStr


class UserGroup(SQLModel, table=True):
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)
    group_id: int | None = Field(default=None, foreign_key="group.id", primary_key=True)


class User(BaseUser, BaseDBModel, table=True):
    username: str = Field(min_length=1, max_length=320, unique=True)
    email: str = Field(min_length=5, max_length=320, unique=True)
    groups: list["Group"] = Relationship(
        back_populates="users", link_model=UserGroup, sa_relationship_kwargs={"lazy": "joined"}
    )


class Group(BaseDBModel, table=True):
    name: str = Field(min_length=1, unique=True)
    users: list[User] = Relationship(back_populates="groups", link_model=UserGroup)
