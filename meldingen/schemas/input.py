from typing import Annotated, Any, Literal, Union

from pydantic import (
    AfterValidator,
    AliasGenerator,
    BaseModel,
    ConfigDict,
    Discriminator,
    EmailStr,
    Field,
    StringConstraints,
    Tag,
)
from pydantic.alias_generators import to_camel
from pydantic_jsonlogic import JSONLogic

from meldingen.models import AnswerTypeEnum, FormIoComponentTypeEnum, FormIoFormDisplayEnum
from meldingen.schemas.types import DateAnswerObject, FormIOConditional, PhoneNumber, ValueLabelObject
from meldingen.validators import create_non_match_validator


class ClassificationInput(BaseModel):
    name: str = Field(min_length=1)
    instructions: str | None = Field(default=None)


class ClassificationCreateInput(ClassificationInput):
    asset_type: int | None = Field(default=None)


class ClassificationUpdateInput(BaseModel):
    name: str | None = Field(min_length=1, default=None)
    instructions: str | None = Field(default=None)
    asset_type: int | None = Field(default=None)


class MeldingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)


class MeldingUpdateInput(BaseModel):
    urgency: Literal[-1, 0, 1] | None = Field(default=None)
    label_ids: list[int] | None = Field(default=None)


class MeldingContactInput(BaseModel):
    email: EmailStr | None = Field(default=None)
    phone: PhoneNumber | None = Field(default=None)


class UserCreateInput(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr


class UserUpdateInput(BaseModel):
    username: str | None = Field(default=None, min_length=3)
    email: EmailStr | None = None


### Form.io ###


class BaseFormInput(BaseModel):
    title: Annotated[str, Field(min_length=3)]
    display: FormIoFormDisplayEnum
    components: list["FormComponentUnion"]


class FormInput(BaseFormInput):
    classification: Annotated[int | None, Field(default=None, gt=0, serialization_alias="classification_id")]


class StaticFormInput(BaseFormInput): ...


class FormPanelComponentInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    label: Annotated[str, Field(min_length=3)]
    title: Annotated[str, Field(min_length=3)]

    key: Annotated[str, Field(min_length=3)]
    type: Literal[FormIoComponentTypeEnum.panel]
    input: bool = False

    components: list["FormComponentInputUnion"]


# Panel is not allowed validator
panel_not_allowed = create_non_match_validator(FormIoComponentTypeEnum.panel, "{value} is not allowed")


class FormComponentInputValidate(BaseModel):
    json_: Annotated[JSONLogic | None, Field(alias="json")] = None
    required: bool = False
    required_error_message: str | None = None


class FormComponentInput(BaseModel):
    label: Annotated[str, Field(min_length=3)]
    description: str | None

    key: Annotated[str, Field(min_length=3)]
    type: Annotated[FormIoComponentTypeEnum, Field(), AfterValidator(panel_not_allowed)]
    input: bool
    validate_: FormComponentInputValidate | None = Field(default=None, alias="validate")
    conditional: FormIOConditional | None = Field(default=None)


class FormTextAreaComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")
    type: Literal[FormIoComponentTypeEnum.text_area]
    auto_expand: bool
    max_char_count: Annotated[int | None, Field(gt=0)] = None


class FormTextFieldComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")
    type: Literal[FormIoComponentTypeEnum.text_field]


class FormComponentValueInput(BaseModel):
    label: Annotated[str, Field(min_length=1)]
    value: Annotated[str, Field(min_length=1)]


class FormRadioComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")
    type: Literal[FormIoComponentTypeEnum.radio]
    values: list[FormComponentValueInput]


class FormCheckboxComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")
    type: Literal[FormIoComponentTypeEnum.checkbox]
    values: list[FormComponentValueInput]


class FormSelectComponentDataInput(BaseModel):
    values: list[FormComponentValueInput]


class FormSelectComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")
    type: Literal[FormIoComponentTypeEnum.select]
    widget: str
    placeholder: str
    data: FormSelectComponentDataInput


class FormDateComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")
    type: Literal[FormIoComponentTypeEnum.date]
    day_range: int


class FormTimeComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")
    type: Literal[FormIoComponentTypeEnum.time]


"""
Use this union when you want to allow only input components, and not the panel.
The panel is a holder for other input components, and therefore cannot be part of the FormComponentInputUnion.
F.e. A panel should be allowed to hold another panel, only a valid input component.
"""
FormComponentInputUnion = Annotated[
    Union[
        FormTextAreaComponentInput,
        FormTextFieldComponentInput,
        FormRadioComponentInput,
        FormCheckboxComponentInput,
        FormSelectComponentInput,
        FormDateComponentInput,
        FormTimeComponentInput,
    ],
    Discriminator("type"),
]

"""
Use this union when you want to allow all components, including the panel.
The panel component is a special case, because it can contain other components.
This is used at the root of a Form, where input components and panels are both allowed.
"""
FormComponentUnion = Annotated[
    Union[
        FormPanelComponentInput,
        FormTextAreaComponentInput,
        FormTextFieldComponentInput,
        FormRadioComponentInput,
        FormCheckboxComponentInput,
        FormSelectComponentInput,
        FormDateComponentInput,
        FormTimeComponentInput,
    ],
    Discriminator("type"),
]


class TextAnswerInput(BaseModel):
    text: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
    type: Literal[AnswerTypeEnum.text]


class TimeAnswerInput(BaseModel):
    time: Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")] | None
    type: Literal[AnswerTypeEnum.time]


class DateAnswerInput(BaseModel):
    date: DateAnswerObject
    type: Literal[AnswerTypeEnum.date]


class ValueLabelAnswerInput(BaseModel):
    values_and_labels: list[ValueLabelObject]
    type: Literal[AnswerTypeEnum.value_label]


AnswerInputUnion = Annotated[
    Union[
        Annotated[TextAnswerInput, Tag(AnswerTypeEnum.text)],
        Annotated[TimeAnswerInput, Tag(AnswerTypeEnum.time)],
        Annotated[DateAnswerInput, Tag(AnswerTypeEnum.date)],
        Annotated[ValueLabelAnswerInput, Tag(AnswerTypeEnum.value_label)],
    ],
    Discriminator("type"),
]


class MailPreviewInput(BaseModel):
    title: str
    preview_text: str
    body_text: str


class CompleteMeldingInput(BaseModel):
    mail_body: str


class AssetTypeInput(BaseModel):
    name: str
    class_name: str
    arguments: dict[str, Any]
    max_assets: int


class AssetTypeUpdateInput(BaseModel):
    name: str | None = None
    class_name: str | None = None
    arguments: dict[str, Any] | None = None
    max_assets: int | None = None


class MeldingAssetInput(BaseModel):
    external_id: str
    asset_type_id: int
