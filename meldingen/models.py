import enum
from datetime import datetime
from typing import Any, Final, Optional, Union

from meldingen_core.models import Answer as BaseAnswer
from meldingen_core.models import Attachment as BaseAttachment
from meldingen_core.models import Classification as BaseClassification
from meldingen_core.models import Form as BaseForm
from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import Question as BaseQuestion
from meldingen_core.models import User as BaseUser
from meldingen_core.statemachine import MeldingStates
from mp_fsm.statemachine import StateAware
from pydantic.alias_generators import to_snake
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, String, Table, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.orderinglist import OrderingList, ordering_list
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, declared_attr, mapped_column, relationship


class BaseDBModel(MappedAsDataclass, DeclarativeBase):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(init=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(init=False, default=func.now(), onupdate=func.now())

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Converts the __name__ of the Class to lowercase snakecase"""
        return to_snake(cls.__name__)


class Classification(AsyncAttrs, BaseDBModel, BaseClassification):
    name: Mapped[str] = mapped_column(String, unique=True)
    form: Mapped[Optional["Form"]] = relationship(default=None, back_populates="classification")


class Melding(AsyncAttrs, BaseDBModel, BaseMelding, StateAware):
    text: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default=MeldingStates.NEW)
    classification_id: Mapped[int | None] = mapped_column(ForeignKey("classification.id"), default=None)
    classification: Mapped[Classification | None] = relationship(default=None)
    token: Mapped[str | None] = mapped_column(String, default=None)
    token_expires: Mapped[DateTime | None] = mapped_column(DateTime, default=None)
    attachments: Mapped[list["Attachment"]] = relationship(
        cascade="save-update, merge, delete, delete-orphan",
        back_populates="melding",
        default_factory=list,
    )


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


# Form


class FormIoComponentTypeEnum(enum.StrEnum):
    """The value of the type field"""

    panel: Final[str] = "panel"
    text_area: Final[str] = "textarea"
    text_field: Final[str] = "textfield"
    checkbox: Final[str] = "selectboxes"
    radio: Final[str] = "radio"
    select: Final[str] = "select"


class FormIoComponent(AsyncAttrs, BaseDBModel):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "form_io_component"

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_on": "type",
        }

    __table_args__ = (
        CheckConstraint("form_id IS NULL OR static_form_id IS NULL", name="only_form_or_static_form_constraint"),
    )

    # Form.io attr's
    label: Mapped[str] = mapped_column(String(), nullable=True)
    key: Mapped[str] = mapped_column(String())

    description: Mapped[str] = mapped_column(String(), nullable=True, default=None)
    type: Mapped[str] = mapped_column(
        Enum(FormIoComponentTypeEnum, name="form_io_component_type"), default=FormIoComponentTypeEnum.text_area
    )
    input: Mapped[bool] = mapped_column(Boolean(), default=True)

    # Internal attr's
    form_id: Mapped[int | None] = mapped_column(ForeignKey("form.id"), default=None, nullable=True)
    form: Mapped[Union["Form", None]] = relationship(
        cascade="save-update, merge, delete",
        back_populates="components",
        default=None,
    )

    static_form_id: Mapped[int | None] = mapped_column(ForeignKey("static_form.id"), default=None, nullable=True)
    static_form: Mapped[Union["StaticForm", None]] = relationship(
        cascade="save-update, merge, delete",
        back_populates="components",
        default=None,
    )

    # Used to keep the order of the components correct
    position: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)

    parent_id: Mapped[int | None] = mapped_column(ForeignKey("form_io_component.id"), default=None, nullable=True)
    parent: Mapped[Optional["FormIoPanelComponent"]] = relationship(
        cascade="save-update, merge, delete",
        back_populates="components",
        default=None,
        remote_side="FormIoPanelComponent.id",
    )


class FormIoPanelComponent(FormIoComponent):
    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.panel,
        }

    components: Mapped[OrderingList[FormIoComponent]] = relationship(
        cascade="save-update, merge, delete, delete-orphan",
        back_populates="parent",
        default_factory=list,
        order_by="FormIoComponent.position",
        collection_class=ordering_list(attr="position", count_from=1),
    )


class FormIoQuestionComponent(FormIoComponent):
    __table_args__ = {"extend_existing": True}

    question_id: Mapped[int | None] = mapped_column(ForeignKey("question.id", ondelete="SET NULL"), default=None)

    @declared_attr
    def question(self) -> Mapped[Union["Question", None]]:
        return relationship("Question", default=None)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {"polymorphic_abstract": True}


class FormIoTextAreaComponent(FormIoQuestionComponent):
    __table_args__ = {"extend_existing": True}

    auto_expand: Mapped[bool] = mapped_column(Boolean(), nullable=True, default=None)
    show_char_count: Mapped[bool] = mapped_column(Boolean(), nullable=True, default=None)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.text_area,
        }


class FormIoTextFieldComponent(FormIoQuestionComponent):
    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.text_field,
        }


class BaseFormIoValuesComponent(FormIoQuestionComponent):
    """
    Base class for all form.io components that can have "values"
    """

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {"polymorphic_abstract": True}

    values: Mapped[OrderingList["FormIoComponentValue"]] = relationship(
        cascade="save-update, merge, delete, delete-orphan",
        back_populates="component",
        default_factory=list,
        order_by="FormIoComponentValue.position",
        collection_class=ordering_list(attr="position", count_from=1),
    )


class FormIoCheckBoxComponent(BaseFormIoValuesComponent):
    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.checkbox,
        }


class FormIoRadioComponent(BaseFormIoValuesComponent):
    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.radio,
        }


class BaseFormIoComponentValue(MappedAsDataclass):
    label: Mapped[str] = mapped_column(String())
    value: Mapped[str] = mapped_column(String())

    # Used to keep the order of the values correct
    position: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)


class FormIoSelectComponentData(BaseDBModel):
    component_id: Mapped[int] = mapped_column(ForeignKey("form_io_component.id"))
    component: Mapped[Optional["FormIoSelectComponent"]] = relationship(
        cascade="save-update, merge, delete",
        back_populates="data",
        default=None,
    )
    values: Mapped[OrderingList["FormIoSelectComponentValue"]] = relationship(
        cascade="save-update, merge, delete, delete-orphan",
        back_populates="data",
        default_factory=list,
        order_by="FormIoSelectComponentValue.position",
        collection_class=ordering_list(attr="position", count_from=1),
    )


class FormIoSelectComponentValue(BaseDBModel, BaseFormIoComponentValue):
    data_id: Mapped[int] = mapped_column(ForeignKey("form_io_select_component_data.id"), init=False)
    data: Mapped["FormIoSelectComponentData"] = relationship(
        cascade="save-update, merge, delete", back_populates="values", default=None
    )


class FormIoSelectComponent(FormIoQuestionComponent):
    __table_args__ = {"extend_existing": True}

    data: Mapped[FormIoSelectComponentData] = relationship(
        cascade="save-update, merge, delete, delete-orphan", back_populates="component", default=None
    )

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.select,
        }


class FormIoComponentValue(BaseDBModel, BaseFormIoComponentValue):
    component_id: Mapped[int | None] = mapped_column(ForeignKey("form_io_component.id"), default=None, nullable=True)
    component: Mapped[Optional[BaseFormIoValuesComponent]] = relationship(
        cascade="save-update, merge, delete",
        back_populates="values",
        default=None,
    )


class FormIoFormDisplayEnum(enum.StrEnum):
    """The value of the display field on the form can be one of the following:
    - form
    - wizard
    - pdf
    """

    form: Final[str] = "form"
    wizard: Final[str] = "wizard"
    pdf: Final[str] = "pdf"


class Form(AsyncAttrs, BaseDBModel, BaseForm):
    title: Mapped[str] = mapped_column(String())

    classification_id: Mapped[int | None] = mapped_column(ForeignKey("classification.id"), default=None, unique=True)
    classification: Mapped[Classification | None] = relationship(default=None, back_populates="form")

    questions: Mapped[list["Question"]] = relationship(
        cascade="save-update, merge, delete, delete-orphan", back_populates="form", default_factory=list, init=False
    )

    # FormIo implementation
    display: Mapped[str] = mapped_column(
        Enum(FormIoFormDisplayEnum, name="form_io_form_display"), default=FormIoFormDisplayEnum.form
    )

    components: Mapped[OrderingList["FormIoComponent"]] = relationship(
        cascade="save-update, merge, delete, delete-orphan",
        back_populates="form",
        default_factory=list,
        order_by="FormIoComponent.position",
        collection_class=ordering_list(attr="position", count_from=1),
    )


class StaticFormTypeEnum(enum.StrEnum):
    primary: Final[str] = "primary"


class StaticForm(AsyncAttrs, BaseDBModel):
    type: Mapped[str] = mapped_column(Enum(StaticFormTypeEnum, name="static_form_type"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String())

    # FormIo implementation
    display: Mapped[str] = mapped_column(
        Enum(FormIoFormDisplayEnum, name="form_io_form_display"), default=FormIoFormDisplayEnum.form
    )

    components: Mapped[OrderingList["FormIoComponent"]] = relationship(
        cascade="save-update, merge, delete, delete-orphan",
        back_populates="static_form",
        default_factory=list,
        order_by="FormIoComponent.position",
        collection_class=ordering_list(attr="position", count_from=1),
    )


class Question(AsyncAttrs, BaseDBModel, BaseQuestion):
    text: Mapped[str] = mapped_column(String())

    form_id: Mapped[int | None] = mapped_column(ForeignKey("form.id", ondelete="SET NULL"), default=None)
    form: Mapped[Form | None] = relationship(default=None)


class Answer(BaseDBModel, BaseAnswer):
    text: Mapped[str] = mapped_column(String())

    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), init=False)
    question: Mapped[Question] = relationship()

    melding_id: Mapped[int] = mapped_column(ForeignKey("melding.id"), init=False)
    melding: Mapped[Melding] = relationship()


class Attachment(BaseDBModel, BaseAttachment):
    file_path: Mapped[str] = mapped_column(String(), init=False)
    original_filename: Mapped[str] = mapped_column(String())

    melding_id: Mapped[int] = mapped_column(ForeignKey("melding.id"), init=False)
    melding: Mapped[Melding] = relationship()
