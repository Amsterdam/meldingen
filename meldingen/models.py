import enum
from typing import Any, Final

from meldingen_core.models import Answer as BaseAnswer
from meldingen_core.models import Classification as BaseClassification
from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import Question as BaseQuestion
from meldingen_core.models import User as BaseUser
from meldingen_core.statemachine import MeldingStates
from mp_fsm.statemachine import StateAware
from pydantic.alias_generators import to_snake
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Table
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.orderinglist import OrderingList, ordering_list
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, declared_attr, mapped_column, relationship


class BaseDBModel(MappedAsDataclass, DeclarativeBase):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Converts the __name__ of the Class to lowercase snakecase"""
        return to_snake(cls.__name__)


class Classification(BaseDBModel, BaseClassification):
    name: Mapped[str] = mapped_column(String, unique=True)


class Melding(BaseDBModel, BaseMelding, StateAware):
    text: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default=MeldingStates.NEW)
    classification_id: Mapped[int | None] = mapped_column(ForeignKey("classification.id"), default=None)
    classification: Mapped[Classification | None] = relationship(default=None)
    token: Mapped[str | None] = mapped_column(String, default=None)
    token_expires: Mapped[DateTime | None] = mapped_column(DateTime, default=None)


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


class FormIoFormDisplayEnum(enum.StrEnum):
    """The value of the display field on the form can be one of the following:
    - form
    - wizard
    - pdf
    """

    form: Final[str] = "form"
    wizard: Final[str] = "wizard"
    pdf: Final[str] = "pdf"


class FormIoForm(AsyncAttrs, BaseDBModel):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "form_io_form"

    @declared_attr.directive
    def __mapper_args__(self) -> dict[str, Any]:
        return {
            "polymorphic_on": "is_primary",
            "polymorphic_identity": False,
        }

    # Form.io attr's
    title: Mapped[str] = mapped_column(String())
    display: Mapped[str] = mapped_column(
        Enum(FormIoFormDisplayEnum, name="form_io_form_display", default=FormIoFormDisplayEnum.form)
    )

    # Internal attr's
    is_primary: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)

    components: Mapped[OrderingList["FormIoComponent"]] = relationship(
        back_populates="form",
        order_by="FormIoComponent.position",
        default_factory=list,
        collection_class=ordering_list(attr="position", count_from=1),
    )


class FormIoPrimaryForm(FormIoForm):
    @declared_attr.directive
    def __mapper_args__(self) -> dict[str, Any]:
        return {
            "polymorphic_identity": True,
        }


class FormIoComponent(AsyncAttrs, BaseDBModel):
    # Form.io attr's
    label: Mapped[str] = mapped_column(String(), nullable=True)
    description: Mapped[str] = mapped_column(String(), nullable=True)

    key: Mapped[str] = mapped_column(String())
    type: Mapped[str] = mapped_column(String())
    input: Mapped[bool] = mapped_column(Boolean(), default=True)

    auto_expand: Mapped[bool] = mapped_column(Boolean(), default=False)
    show_char_count: Mapped[bool] = mapped_column(Boolean(), default=False)

    # Internal attr's
    form_id: Mapped[int] = mapped_column(ForeignKey("form_io_form.id"), default=None)
    form: Mapped["FormIoForm"] = relationship(back_populates="components", default_factory=list)

    # Used to keep the order of the components correct
    position: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)


class Question(BaseDBModel, BaseQuestion):
    text: Mapped[str] = mapped_column(String())


class Answer(BaseDBModel, BaseAnswer):
    text: Mapped[str] = mapped_column(String())

    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"))
    question: Mapped[Question] = relationship()

    melding_id: Mapped[int] = mapped_column(ForeignKey("melding.id"))
    melding: Mapped[Melding] = relationship()
