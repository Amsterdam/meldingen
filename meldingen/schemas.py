from datetime import datetime
from typing import Annotated, Any, Union

from meldingen_core.models import Classification, User
from pydantic import AfterValidator, AliasGenerator, BaseModel, ConfigDict, Discriminator, EmailStr, Field, Tag
from pydantic.alias_generators import to_camel

from meldingen.models import FormIoComponentTypeEnum, FormIoFormDisplayEnum
from meldingen.validators import create_non_match_validator


class BaseOutputModel(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime


class ClassificationInput(BaseModel, Classification):
    name: str = Field(min_length=1)


class ClassificationOutput(BaseOutputModel, Classification):
    form: int | None = None


class MeldingInput(BaseModel):
    text: str = Field(min_length=1)


class MeldingOutput(BaseOutputModel):
    text: str
    state: str
    classification: int | None = Field(default=None)


class MeldingCreateOutput(MeldingOutput):
    token: str


class UserCreateInput(BaseModel, User):
    username: str = Field(min_length=3)
    email: EmailStr


class UserOutput(BaseOutputModel):
    email: str
    username: str


class UserUpdateInput(BaseModel):
    username: str | None = Field(default=None, min_length=3)
    email: EmailStr | None = None


### Form.io ###


def component_discriminator(value: Any) -> str | None:
    """
    The component discriminator knows the difference between a "panel" and a "normal" component.
    It helps pydantic to make the correct choice when to validate a given dict to a specific model.

    Example:
        components: list[
            Annotated[
                Union[
                    Annotated["FormPanelComponentInput", Tag(FormIoComponentTypeEnum.panel)],
                    Annotated["FormTextAreaComponentInput", Tag(FormIoComponentTypeEnum.text_area)],
                    Annotated["FormComponentInput", Tag("component")],
                ],
                Discriminator(component_discriminator),
            ]
        ]
    """
    if isinstance(value, dict):
        return value.get("type")
    elif isinstance(value, FormPanelComponentInput):
        return FormIoComponentTypeEnum.panel
    elif isinstance(value, FormTextAreaComponentInput):
        return FormIoComponentTypeEnum.text_area
    elif isinstance(value, FormTextFieldComponentInput):
        return FormIoComponentTypeEnum.text_field
    elif isinstance(value, FormRadioComponentInput):
        return FormIoComponentTypeEnum.radio
    elif isinstance(value, FormCheckboxComponentInput):
        return FormIoComponentTypeEnum.checkbox
    elif isinstance(value, FormSelectComponentInput):
        return FormIoComponentTypeEnum.select

    return None


class BaseFormInput(BaseModel):
    title: Annotated[str, Field(min_length=3)]
    display: FormIoFormDisplayEnum
    components: list[
        Annotated[
            Union[
                Annotated["FormPanelComponentInput", Tag(FormIoComponentTypeEnum.panel)],
                Annotated["FormTextAreaComponentInput", Tag(FormIoComponentTypeEnum.text_area)],
                Annotated["FormTextFieldComponentInput", Tag(FormIoComponentTypeEnum.text_field)],
                Annotated["FormRadioComponentInput", Tag(FormIoComponentTypeEnum.radio)],
                Annotated["FormCheckboxComponentInput", Tag(FormIoComponentTypeEnum.checkbox)],
                Annotated["FormSelectComponentInput", Tag(FormIoComponentTypeEnum.select)],
            ],
            Discriminator(component_discriminator),
        ]
    ]


class FormInput(BaseFormInput):
    classification: Annotated[int | None, Field(default=None, gt=0, serialization_alias="classification_id")]


class StaticFormInput(BaseFormInput): ...


class FormPanelComponentInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    label: Annotated[str, Field(min_length=3)]

    key: Annotated[str, Field(min_length=3)]
    type: Annotated[FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.panel)]
    input: bool = False

    components: list[
        Annotated[
            Union[
                Annotated["FormTextAreaComponentInput", Tag(FormIoComponentTypeEnum.text_area)],
                Annotated["FormTextFieldComponentInput", Tag(FormIoComponentTypeEnum.text_field)],
                Annotated["FormRadioComponentInput", Tag(FormIoComponentTypeEnum.radio)],
                Annotated["FormCheckboxComponentInput", Tag(FormIoComponentTypeEnum.checkbox)],
                Annotated["FormSelectComponentInput", Tag(FormIoComponentTypeEnum.select)],
            ],
            Discriminator(component_discriminator),
        ]
    ]


# Panel is not allowed validator
panel_not_allowed = create_non_match_validator(FormIoComponentTypeEnum.panel, "{value} is not allowed")


class FormComponentInput(BaseModel):
    label: Annotated[str, Field(min_length=3)]
    description: str | None

    key: Annotated[str, Field(min_length=3)]
    type: Annotated[FormIoComponentTypeEnum, Field(), AfterValidator(panel_not_allowed)]
    input: bool


class FormTextAreaComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    type: Annotated[FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.text_area)]
    auto_expand: bool
    show_char_count: bool


class FormTextFieldComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    type: Annotated[FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.text_field)]


class FormComponentValueInput(BaseModel):
    label: Annotated[str, Field(min_length=1)]
    value: Annotated[str, Field(min_length=1)]


class FormRadioComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    type: Annotated[FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.radio)]
    values: list[FormComponentValueInput]


class FormCheckboxComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    type: Annotated[FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.checkbox)]
    values: list[FormComponentValueInput]


class FormSelectComponentDataInput(BaseModel):
    values: list[FormComponentValueInput]


class FormSelectComponentInput(FormComponentInput):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    type: Annotated[FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.select)]
    widget: str
    data: FormSelectComponentDataInput


class AnswerInput(BaseModel):
    text: str = Field(min_length=1)


class AnswerOutput(BaseOutputModel): ...


class AttachmentOutput(BaseOutputModel):
    original_filename: str
