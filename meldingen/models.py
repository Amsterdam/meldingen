import enum
from datetime import datetime
from typing import Any, Optional, Union

from geoalchemy2 import Geometry, WKBElement
from meldingen_core.models import Answer as BaseAnswer
from meldingen_core.models import Asset as BaseAsset
from meldingen_core.models import AssetType as BaseAssetType
from meldingen_core.models import Attachment as BaseAttachment
from meldingen_core.models import Classification as BaseClassification
from meldingen_core.models import Form as BaseForm
from meldingen_core.models import Melding as BaseMelding
from meldingen_core.models import Question as BaseQuestion
from meldingen_core.models import User as BaseUser
from meldingen_core.statemachine import MeldingStates
from mp_fsm.statemachine import StateAware
from pydantic.alias_generators import to_snake
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)
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


class AssetType(BaseDBModel, BaseAssetType):
    name: Mapped[str] = mapped_column(String, unique=True)
    class_name: Mapped[str] = mapped_column(String)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON)
    max_assets: Mapped[int] = mapped_column(Integer)


class Asset(BaseDBModel, BaseAsset):
    __table_args__ = (UniqueConstraint("external_id", "type_id"),)

    external_id: Mapped[str] = mapped_column(String)
    type_id: Mapped[int] = mapped_column(ForeignKey(AssetType.id), init=False)
    type: Mapped[AssetType] = relationship()


class Classification(AsyncAttrs, BaseDBModel, BaseClassification):
    name: Mapped[str] = mapped_column(String, unique=True)
    form: Mapped[Optional["Form"]] = relationship(default=None, back_populates="classification")
    asset_type_id: Mapped[int | None] = mapped_column(ForeignKey(AssetType.id), default=None)
    asset_type: Mapped[AssetType | None] = relationship(default=None)


asset_melding = Table(
    "asset_melding",
    BaseDBModel.metadata,
    Column("asset_id", Integer, ForeignKey(Asset.id), primary_key=True),
    Column("melding_id", Integer, ForeignKey("melding.id"), primary_key=True),
)


class Melding(AsyncAttrs, BaseDBModel, BaseMelding, StateAware):
    public_id: Mapped[str] = mapped_column(String(), unique=True, init=False)
    text: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default=MeldingStates.NEW)
    classification_id: Mapped[int | None] = mapped_column(ForeignKey("classification.id"), default=None)
    classification: Mapped[Classification | None] = relationship(default=None, lazy="joined")
    token: Mapped[str | None] = mapped_column(String, default=None)
    token_expires: Mapped[DateTime | None] = mapped_column(DateTime, default=None)
    attachments: Mapped[list["Attachment"]] = relationship(
        cascade="save-update, merge, delete, delete-orphan",
        back_populates="melding",
        default_factory=list,
    )
    geo_location: Mapped[WKBElement | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326), default=None  # WGS84
    )
    street: Mapped[str | None] = mapped_column(String, default=None)
    house_number: Mapped[int | None] = mapped_column(Integer, default=None)
    house_number_addition: Mapped[str | None] = mapped_column(String, default=None)
    postal_code: Mapped[str | None] = mapped_column(String(16), default=None)
    city: Mapped[str | None] = mapped_column(String, default=None)
    email: Mapped[str | None] = mapped_column(String(254), default=None)
    phone: Mapped[str | None] = mapped_column(String(50), default=None)
    assets: Mapped[list[Asset]] = relationship(secondary=asset_melding, default_factory=list)
    answers: Mapped[list["Answer"]] = relationship(
        "Answer", back_populates="melding", cascade="save-update, merge, delete, delete-orphan", default_factory=list
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

    panel = "panel"
    text_area = "textarea"
    text_field = "textfield"
    checkbox = "selectboxes"
    radio = "radio"
    select = "select"
    date = "date"
    time = "time"


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
    conditional: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=None)


class FormIoPanelComponent(FormIoComponent):
    __table_args__ = {"extend_existing": True}

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.panel,
        }

    title: Mapped[str] = mapped_column(String(), default=None, nullable=True)

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
    jsonlogic: Mapped[str | None] = mapped_column(String(), nullable=True, default=None)
    required: Mapped[bool] = mapped_column(Boolean(), nullable=True, default=None)
    required_error_message: Mapped[str | None] = mapped_column(String(), nullable=True, default=None)

    @declared_attr
    def question(self) -> Mapped[Union["Question", None]]:
        return relationship("Question", back_populates="component", default=None)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {"polymorphic_abstract": True}


class FormIoTextAreaComponent(FormIoQuestionComponent):
    __table_args__ = {"extend_existing": True}

    auto_expand: Mapped[bool] = mapped_column(Boolean(), nullable=True, default=None)
    max_char_count: Mapped[int | None] = mapped_column(Integer(), nullable=True, default=None)

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


class FormIoSelectComponentData(AsyncAttrs, BaseDBModel):
    component_id: Mapped[int] = mapped_column(ForeignKey("form_io_component.id"), init=False)
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

    widget: Mapped[str] = mapped_column(String(), nullable=True, default=None)
    placeholder: Mapped[str] = mapped_column(String(), nullable=True, default=None)
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


class FormIoDateComponent(FormIoQuestionComponent):
    # A component that allows the user to select a date in the past or today.
    __table_args__ = {"extend_existing": True}

    """
    The amount of days a date in the past can be selected from today.
    For example, if today is 2024-01-10 and day_range is 7, the user can select dates from 2024-01-03 to 2024-01-10.
    """
    day_range: Mapped[int | None] = mapped_column(Integer(), nullable=True, default=None)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.date,
        }


class FormIoTimeComponent(FormIoQuestionComponent):
    # A component that allows the user to select a time of day.
    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": FormIoComponentTypeEnum.time,
        }


class FormIoFormDisplayEnum(enum.StrEnum):
    """The value of the display field on the form can be one of the following:
    - form
    - wizard
    - pdf
    """

    form = "form"
    wizard = "wizard"
    pdf = "pdf"


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
    primary = "primary"
    attachments = "attachments"
    contact = "contact"


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

    component: Mapped[FormIoQuestionComponent | None] = relationship(default=None)


class AnswerTypeEnum(enum.StrEnum):
    text = "text"
    time = "time"


# Mapping from FormIoComponentTypeEnum to AnswerTypeEnum
FormIoComponentToAnswerTypeMap = {
    FormIoComponentTypeEnum.text_area: AnswerTypeEnum.text,
    FormIoComponentTypeEnum.text_field: AnswerTypeEnum.text,
    FormIoComponentTypeEnum.time: AnswerTypeEnum.time,
}


class Answer(AsyncAttrs, BaseAnswer, BaseDBModel, kw_only=True):
    """This class uses kw_only to bypass the issue where fields with default values
    cannot come before fields without default values in the generated __init__ method."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return "answer"

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_on": "type",
            "polymorphic_abstract": True,
        }

    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), init=False)
    question: Mapped[Question] = relationship()

    melding_id: Mapped[int] = mapped_column(ForeignKey("melding.id"), init=False)
    melding: Mapped[Melding] = relationship(back_populates="answers", default_factory=list)
    type: Mapped[str] = mapped_column(Enum(AnswerTypeEnum, name="answer_type"), default=AnswerTypeEnum.text)


class TextAnswer(Answer):
    __table_args__ = {"extend_existing": True}

    text: Mapped[str] = mapped_column(String(), nullable=True)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": AnswerTypeEnum.text,
        }


class TimeAnswer(Answer):
    """Answer type for time values. Stored as hh:mm string,
    because it's only used as a simple display of the user's input"""

    __table_args__ = {"extend_existing": True}

    time: Mapped[str] = mapped_column(String(), nullable=True)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "polymorphic_identity": AnswerTypeEnum.time,
        }


class Attachment(AsyncAttrs, BaseDBModel, BaseAttachment):
    file_path: Mapped[str] = mapped_column(String(), init=False)
    original_filename: Mapped[str] = mapped_column(String())
    original_media_type: Mapped[str] = mapped_column(String())

    melding_id: Mapped[int] = mapped_column(ForeignKey("melding.id"), init=False)
    melding: Mapped[Melding] = relationship()

    optimized_path: Mapped[str | None] = mapped_column(String(), default=None)
    optimized_media_type: Mapped[str | None] = mapped_column(String(), default=None)
    thumbnail_path: Mapped[str | None] = mapped_column(String(), default=None)
    thumbnail_media_type: Mapped[str | None] = mapped_column(String(), default=None)
