from meldingen_core.models import Classification, User
from pydantic import AliasGenerator, BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


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


class FormOnlyOutput(BaseModel):
    title: str
    display: str


class FormOutput(BaseModel):
    title: str
    display: str
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


class FormUpdateInput(BaseModel):
    title: str
    components: list["FormComponentUpdateInput"]


class FormComponentUpdateInput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(alias=to_camel))

    label: str
    description: str

    key: str
    type: str
    input: bool

    auto_expand: bool
    show_char_count: bool
