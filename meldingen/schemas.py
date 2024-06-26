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


class BaseFormOutput(BaseModel):
    title: str
    display: str
    created_at: datetime
    updated_at: datetime


class FormOnlyOutput(BaseFormOutput):
    id: int
    classification: int | None = None


class FormOutput(FormOnlyOutput):
    components: list[Union["FormComponentOutput", "FormPanelComponentOutput"]]


class StaticFormOutput(BaseFormOutput):
    type: str
    components: list[Union["FormComponentOutput", "FormPanelComponentOutput"]]


class FormComponentValueOutput(BaseModel):
    label: str
    value: str
    position: int


class FormComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str
    description: str

    key: str
    type: str
    input: bool

    auto_expand: bool
    show_char_count: bool

    position: int

    question: int | None = None

    values: list[FormComponentValueOutput] | None = None


class FormPanelComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str

    key: str
    type: str
    input: bool

    position: int

    components: list[FormComponentOutput]


def component_discriminator(value: Any) -> str:
    """
    The component discriminator knows the difference between a "panel" and a "normal" component.
    It helps pydantic to make the correct choice when to validate a given dict to a specific model.

    Example:
        components: list[
            Annotated[
                Union[
                    Annotated["FormPanelComponentInput", Tag("panel")],
                    Annotated["FormComponentInput", Tag("component")],
                ],
                Discriminator(_component_discriminator),
            ]
        ]
    """
    if isinstance(value, dict):
        if value.get("type") == FormIoComponentTypeEnum.panel:
            return "panel"
        elif value.get("type") == FormIoComponentTypeEnum.radio:
            return "values"
        elif value.get("type") == FormIoComponentTypeEnum.checkbox:
            return "values"
    elif isinstance(value, FormPanelComponentInput):
        return "panel"
    elif isinstance(value, FormValuesComponentInput):
        return "values"

    return "component"


class BaseFormInput(BaseModel):
    title: Annotated[str, Field(min_length=3)]
    display: FormIoFormDisplayEnum
    components: list[
        Annotated[
            Union[
                Annotated["FormPanelComponentInput", Tag("panel")],
                Annotated["FormValuesComponentInput", Tag("values")],
                Annotated["FormComponentInput", Tag("component")],
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

    components: list["FormComponentInput"]


# Panel is not allowed validator
panel_not_allowed = create_non_match_validator(FormIoComponentTypeEnum.panel, "{value} is not allowed")


class FormComponentInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel))

    label: Annotated[str, Field(min_length=3)]
    description: str | None

    key: Annotated[str, Field(min_length=3)]
    type: Annotated[
        FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.text_area), AfterValidator(panel_not_allowed)
    ]
    input: bool

    auto_expand: bool
    show_char_count: bool


class FormValuesComponentInput(FormComponentInput):
    type: Annotated[FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.radio)]
    values: list["FormComponentValueInput"]


class FormComponentValueInput(BaseModel):
    label: Annotated[str, Field(min_length=1)]
    value: Annotated[str, Field(min_length=1)]


class AnswerInput(BaseModel):
    text: str = Field(min_length=1)


class AnswerOutput(BaseOutputModel): ...
