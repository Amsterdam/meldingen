from typing import Annotated, Any, Callable, Union

from meldingen_core.models import Classification, User
from pydantic import AfterValidator, AliasGenerator, BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from meldingen.models import FormIoComponentTypeEnum, FormIoFormDisplayEnum


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


def create_exact_match_validator(match_value: Any, error_msg: str) -> Callable[[Any], Any]:
    def validator(value: Any) -> Any:
        assert value == match_value, error_msg
        return value

    return validator


def create_non_match_validator(match_value: Any, error_msg: str) -> Callable[[Any], Any]:
    def validator(value: Any) -> Any:
        assert value != match_value, error_msg
        return value

    return validator


_only_type_panel_validator = create_exact_match_validator(
    FormIoComponentTypeEnum.panel, error_msg="only panel is allowed!"
)
_anything_but_type_panel_validator = create_non_match_validator(
    FormIoComponentTypeEnum.panel, error_msg="panel is not allowed!"
)


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


class FormPanelComponentOutput(FormComponentOutput):
    components: list[FormComponentOutput]


class FormCreateInput(BaseModel):
    title: str = Field(min_length=3)
    display: FormIoFormDisplayEnum
    classification: int | None = Field(default=None, gt=0, serialization_alias="classification_id")
    components: list[Union["FormComponentCreateInput", "FormPanelComponentCreateInput"]]


class FormComponentCreateInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel))

    label: str
    description: str

    key: str
    type: Annotated[FormIoComponentTypeEnum, AfterValidator(_anything_but_type_panel_validator)]
    input: bool

    auto_expand: bool
    show_char_count: bool


class FormPanelComponentCreateInput(FormComponentCreateInput):
    type: Annotated[FormIoComponentTypeEnum, AfterValidator(_only_type_panel_validator)]

    components: list["FormComponentCreateInput"]


class PrimaryFormUpdateInput(BaseModel):
    title: str
    components: list[Union["FormComponentUpdateInput", "FormPanelComponentUpdateInput"]]


class FormUpdateInput(PrimaryFormUpdateInput):
    display: FormIoFormDisplayEnum
    classification: int | None = Field(default=None, gt=0, serialization_alias="classification_id")


class FormComponentUpdateInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel))

    label: str
    description: str

    key: str
    type: Annotated[FormIoComponentTypeEnum, AfterValidator(_anything_but_type_panel_validator)]
    input: bool

    auto_expand: bool
    show_char_count: bool


class FormPanelComponentUpdateInput(FormComponentUpdateInput):
    type: Annotated[FormIoComponentTypeEnum, AfterValidator(_only_type_panel_validator)]

    components: list["FormComponentUpdateInput"]
