from typing import Annotated, Literal, Union

from meldingen_core.models import Classification, User
from pydantic import AfterValidator, AliasGenerator, BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from meldingen.models import FormIoComponentTypeEnum, FormIoFormDisplayEnum
from meldingen.validators import create_match_validator, create_non_match_validator


class ClassificationInput(BaseModel, Classification):
    name: str = Field(min_length=1)


class ClassificationOutput(BaseModel, Classification):
    id: int


class MeldingInput(BaseModel):
    text: str = Field(min_length=1)


class MeldingOutput(BaseModel):
    id: int
    text: str
    state: str
    classification: int | None = Field(default=None)


class MeldingCreateOutput(MeldingOutput):
    token: str


class UserCreateInput(BaseModel, User):
    username: str = Field(min_length=3)
    email: EmailStr


class UserOutput(BaseModel):
    id: int
    email: str
    username: str


class UserUpdateInput(BaseModel):
    username: str | None = Field(default=None, min_length=3)
    email: EmailStr | None = None


### Form.io ###


class BaseFormOutput(BaseModel):
    title: str
    display: str


class PrimaryFormOutput(BaseFormOutput):
    components: list[Union["FormComponentOutput", "FormPanelComponentOutput"]]


class FormOnlyOutput(BaseFormOutput):
    id: int
    classification: int | None = None


class FormOutput(FormOnlyOutput):
    components: list[Union["FormComponentOutput", "FormPanelComponentOutput"]]


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


class FormPanelComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str

    key: str
    type: str
    input: bool

    position: int

    components: list[FormComponentOutput]


_only_type_panel_validator = create_match_validator(FormIoComponentTypeEnum.panel, error_msg="only panel is allowed!")
_anything_but_type_panel_validator = create_non_match_validator(
    FormIoComponentTypeEnum.panel, error_msg="panel is not allowed!"
)


class PrimaryFormInput(BaseModel):
    title: Annotated[str, Field(min_length=3)]
    components: list[
        Annotated[Union["FormComponentInput", "FormPanelComponentInput"], Field(union_mode="left_to_right")]
    ]


class FormInput(PrimaryFormInput):
    display: FormIoFormDisplayEnum
    classification: Annotated[int | None, Field(default=None, gt=0, serialization_alias="classification_id")]


class FormComponentInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    label: Annotated[str, Field(min_length=3)]
    description: Annotated[str, Field(min_length=3)]

    key: Annotated[str, Field(min_length=3)]
    type: Annotated[
        FormIoComponentTypeEnum,
        Field(FormIoComponentTypeEnum.text_area),
        AfterValidator(_anything_but_type_panel_validator),
    ]
    input: bool

    auto_expand: bool
    show_char_count: bool


class FormPanelComponentInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel), extra="forbid")

    label: Annotated[str, Field(min_length=3)]

    key: Annotated[str, Field(min_length=3)]
    type: Annotated[
        FormIoComponentTypeEnum, Field(FormIoComponentTypeEnum.panel), AfterValidator(_only_type_panel_validator)
    ]
    input: bool = False

    components: list[FormComponentInput]
