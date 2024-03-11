import enum
import re
from typing import Final

from meldingen_core.models import Classification as BaseClassification
from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import User as BaseUser
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Table
from sqlalchemy.ext.orderinglist import OrderingList, ordering_list
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, declared_attr, mapped_column, relationship


class BaseDBModel(MappedAsDataclass, DeclarativeBase):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Converst the __name__ of the Class to lowercase snakecase"""
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()


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


class UserCreateInput(BaseModel, BaseUser):
    username: str = Field(min_length=3)
    email: EmailStr


class UserOutput(BaseModel):
    id: int
    email: str
    username: str


class UserUpdateInput(BaseModel):
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


class FormsIoFormDisplayEnum(enum.Enum):
    """The value of the display field on the form can be one of the following:
    - form
    - wizard
    - pdf
    """

    form: Final[str] = "form"
    wizard: Final[str] = "wizard"
    pdf: Final[str] = "pdf"


class FormsIoForm(BaseDBModel):
    # Forms.io attr's
    display: Mapped[str] = mapped_column(Enum(FormsIoFormDisplayEnum, name="forms_io_form_display", default="form"))

    # Internal attr's

    components: Mapped[OrderingList["FormsIoComponent"]] = relationship(
        back_populates="form",
        order_by="FormsIoComponent.position",
        default_factory=ordering_list("position", count_from=1),
    )


class FormsIoComponent(BaseDBModel):
    # Forms.io attr's

    label: Mapped[str] = mapped_column(String(), nullable=True)
    description: Mapped[str] = mapped_column(String(), nullable=True)

    key: Mapped[str] = mapped_column(String())
    type: Mapped[str] = mapped_column(String())
    input: Mapped[bool] = mapped_column(Boolean(), default=True)

    auto_expand: Mapped[bool] = mapped_column(Boolean(), default=False)
    show_char_count: Mapped[bool] = mapped_column(Boolean(), default=False)

    # Internal attr's

    form_id: Mapped[int] = mapped_column(ForeignKey("forms_io_form.id"), default=None)
    form: Mapped["FormsIoForm"] = relationship(back_populates="components", default_factory=list)

    # Used to keep the order of the components correct
    position: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
