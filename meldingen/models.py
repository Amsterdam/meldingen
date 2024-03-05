from meldingen_core.models import Classification as BaseClassification
from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import User as BaseUser
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, declared_attr, mapped_column, relationship


class BaseDBModel(MappedAsDataclass, DeclarativeBase):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class ClassificationInput(BaseModel, BaseClassification):
    name: str = Field(min_length=1)


class ClassificationOutput(BaseModel, BaseClassification):
    id: int


class Classification(BaseDBModel, BaseClassification):
    name: Mapped[str] = mapped_column(String, unique=True)


class MeldingInput(BaseModel):
    text: str = Field(min_length=1)


class MeldingOutput(BaseModel):
    id: int
    text: str


class Melding(BaseDBModel, BaseMelding):
    text: Mapped[str] = mapped_column(String)
    classification_id: Mapped[int | None] = mapped_column(ForeignKey("classification.id"), default=None)
    classification: Mapped[Classification | None] = relationship(default=None)


class UserInput(BaseModel, BaseUser):
    username: str = Field(min_length=3)
    email: EmailStr


class UserOutput(BaseModel):
    id: int
    email: str
    username: str


class UserPartialInput(BaseModel):
    username: str | None = Field(default=None, min_length=3)
    email: EmailStr | None = None


user_group = Table(
    "user_group",
    BaseDBModel.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("group.id"), primary_key=True),
)


class User(BaseDBModel, BaseUser):
    username: Mapped[str] = mapped_column(String(320), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    groups: Mapped[list["Group"]] = relationship(
        secondary=user_group, back_populates="users", lazy="joined", default_factory=list
    )


class Group(BaseDBModel):
    name: Mapped[str] = mapped_column(unique=True)
    users: Mapped[list[User]] = relationship(secondary=user_group, back_populates="groups", default_factory=list)
