from typing import Optional

from meldingen_core.models import Classification as BaseClassification
from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import User as BaseUser
from pydantic import EmailStr, BaseModel
from sqlalchemy import String, Table, Integer, Column, ForeignKey
from sqlalchemy.orm import MappedAsDataclass, DeclarativeBase, Mapped, mapped_column, declared_attr, relationship


class BaseDBModel(MappedAsDataclass, DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class Classification(BaseDBModel, BaseClassification): ...


class MeldingCreateInput(BaseModel):
    text: str


class Melding(BaseDBModel, BaseMelding):
    text: Mapped[str] = mapped_column(String)
    classification_id: Mapped[int] = mapped_column(ForeignKey("classification.id"), nullable=True)
    classification: Mapped[Classification | None] = relationship()


class UserInput(BaseUser, BaseModel):
    email: EmailStr


class UserPartialInput(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


user_group = Table(
    "user_group",
    BaseDBModel.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("group.id"), primary_key=True),
)


class User(BaseDBModel, BaseUser):
    username: Mapped[str] = mapped_column(String(320), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    groups: Mapped[list["Group"]] = relationship(secondary=user_group, back_populates="users", lazy="joined")


class Group(BaseDBModel):
    name: Mapped[str] = mapped_column(unique=True)
    users: Mapped[list[User]] = relationship(secondary=user_group, back_populates="groups")
