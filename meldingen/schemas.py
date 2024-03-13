from meldingen_core.models import Classification, User
from pydantic import BaseModel, EmailStr, Field


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
