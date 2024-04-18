from meldingen_core.models import Classification, User
from pydantic import AliasGenerator, BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from meldingen.models import FormIoFormDisplayEnum


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


class BaseFormOutput(BaseModel):
    title: str
    display: str


class PrimaryFormOutput(BaseFormOutput):
    components: list["FormComponentOutput"]


class FormOnlyOutput(BaseFormOutput):
    id: int
    classification: int | None = None


class FormOutput(FormOnlyOutput):
    components: list["FormComponentOutput"]


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


class FormCreateInput(BaseModel):
    title: str = Field(min_length=3)
    display: FormIoFormDisplayEnum
    classification: int | None = Field(default=None, gt=0, serialization_alias="classification_id")
    components: list["FormComponentCreateInput"]


class FormComponentCreateInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel))

    label: str
    description: str

    key: str
    type: str
    input: bool

    auto_expand: bool
    show_char_count: bool


class PrimaryFormUpdateInput(BaseModel):
    title: str
    components: list["FormComponentUpdateInput"]


class FormUpdateInput(PrimaryFormUpdateInput):
    display: FormIoFormDisplayEnum
    classification: int | None = Field(default=None, gt=0, serialization_alias="classification_id")


class FormComponentUpdateInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel))

    label: str
    description: str

    key: str
    type: str
    input: bool

    auto_expand: bool
    show_char_count: bool
