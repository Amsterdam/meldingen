from datetime import datetime
from typing import Annotated, Any, Literal, Union, final

from pydantic import AliasGenerator, BaseModel, ConfigDict, EmailStr, Field, field_serializer
from pydantic.alias_generators import to_camel
from pydantic_jsonlogic import JSONLogic

from meldingen.models import AnswerTypeEnum
from meldingen.schemas.types import DateAnswerObject, FormIOConditional, GeoJson, PhoneNumber, ValueLabelObject

### Form.io ###


class BaseOutputModel(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, created_at: datetime) -> str:
        return created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    @field_serializer("updated_at")
    def serialize_updated_at(self, updated_at: datetime) -> str:
        return updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")


class BaseFormOutput(BaseOutputModel):
    title: str
    display: str


class AssetTypeOutput(BaseOutputModel):
    name: str
    class_name: str
    arguments: dict[str, Any]
    max_assets: int


class SimpleClassificationOutput(BaseOutputModel):
    name: str
    asset_type: AssetTypeOutput | None = Field(default=None)


class ClassificationOutput(BaseOutputModel):
    name: str
    form: int | None = None
    asset_type: int | None = None


class MeldingOutput(BaseOutputModel):
    public_id: str
    text: str
    state: str
    classification: SimpleClassificationOutput | None = Field(default=None)
    geo_location: GeoJson | None = Field(default=None)
    street: str | None = Field(default=None)
    house_number: int | None = Field(default=None)
    house_number_addition: str | None = Field(default=None)
    postal_code: str | None = Field(default=None)
    city: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)
    phone: PhoneNumber | None = Field(default=None)


class MeldingWithTokenOutput(MeldingOutput):
    token: str


class MeldingCreateOutput(MeldingWithTokenOutput):
    pass


class MeldingUpdateOutput(MeldingWithTokenOutput):
    pass


class SimpleStaticFormOutput(BaseFormOutput):
    type: str


class StaticFormOutput(SimpleStaticFormOutput):
    components: list[
        Union[
            "StaticFormPanelComponentOutput",
            "StaticFormTextAreaComponentOutput",
            "StaticFormTextFieldInputComponentOutput",
            "StaticFormCheckboxComponentOutput",
            "StaticFormRadioComponentOutput",
            "StaticFormSelectComponentOutput",
        ]
    ]


class SimpleFormOutput(BaseFormOutput):
    id: int
    classification: int | None = None


class FormOutput(SimpleFormOutput):
    components: list[
        Union[
            "FormPanelComponentOutput",
            "FormTextAreaComponentOutput",
            "FormTextFieldInputComponentOutput",
            "FormCheckboxComponentOutput",
            "FormRadioComponentOutput",
            "FormSelectComponentOutput",
            "FormDateComponentOutput",
            "FormTimeComponentOutput",
        ]
    ]


class BaseFormPanelComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    title: str
    label: str

    key: str
    type: str
    input: bool

    position: int
    conditional: FormIOConditional | None = Field(default=None)


class StaticFormPanelComponentOutput(BaseFormPanelComponentOutput):
    components: list[
        Union[
            "StaticFormTextAreaComponentOutput",
            "StaticFormTextFieldInputComponentOutput",
            "StaticFormCheckboxComponentOutput",
            "StaticFormRadioComponentOutput",
            "StaticFormSelectComponentOutput",
        ]
    ]


class FormPanelComponentOutput(BaseFormPanelComponentOutput):
    components: list[
        Union[
            "FormTextAreaComponentOutput",
            "FormTextFieldInputComponentOutput",
            "FormCheckboxComponentOutput",
            "FormRadioComponentOutput",
            "FormSelectComponentOutput",
            "FormDateComponentOutput",
            "FormTimeComponentOutput",
        ]
    ]


class FormComponentOutputValidate(BaseModel):
    json_: Annotated[JSONLogic | None, Field(alias="json")] = None
    required: bool
    required_error_message: str | None


class BaseFormComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str
    description: str

    key: str
    type: str
    input: bool

    position: int

    validate_: FormComponentOutputValidate | None = Field(alias="validate", default=None)
    conditional: FormIOConditional | None = Field(default=None)


class StaticFormTextAreaComponentOutput(BaseFormComponentOutput):
    auto_expand: bool
    max_char_count: int | None


class StaticFormTextFieldInputComponentOutput(BaseFormComponentOutput): ...


class StaticFormCheckboxComponentOutput(BaseFormComponentOutput):
    values: list["FormComponentValueOutput"]


class StaticFormRadioComponentOutput(BaseFormComponentOutput):
    values: list["FormComponentValueOutput"]


class FormComponentValueOutput(BaseModel):
    label: str
    value: str
    position: int


class FormSelectComponentDataOutput(BaseModel):
    values: list[FormComponentValueOutput]


class StaticFormSelectComponentOutput(BaseFormComponentOutput):
    widget: str
    placeholder: str
    data: FormSelectComponentDataOutput


class FormTextAreaComponentOutput(StaticFormTextAreaComponentOutput):
    question: int


class FormTextFieldInputComponentOutput(StaticFormTextFieldInputComponentOutput):
    question: int


class FormCheckboxComponentOutput(StaticFormCheckboxComponentOutput):
    question: int


class FormRadioComponentOutput(StaticFormRadioComponentOutput):
    question: int


class FormSelectComponentOutput(StaticFormSelectComponentOutput):
    question: int


class FormDateComponentOutput(BaseFormComponentOutput):
    day_range: int | None = Field(default=None)
    question: int


class FormTimeComponentOutput(BaseFormComponentOutput):
    question: int


class AnswerOutput(BaseOutputModel):
    type: str


class TextAnswerOutput(AnswerOutput):
    text: str
    type: Literal[AnswerTypeEnum.text]


class TimeAnswerOutput(AnswerOutput):
    time: str
    type: Literal[AnswerTypeEnum.time]


class DateAnswerOutput(AnswerOutput):
    date: DateAnswerObject
    type: Literal[AnswerTypeEnum.date]


class ValueLabelAnswerOutput(AnswerOutput):
    value_and_labels: list[ValueLabelObject]
    type: Literal[AnswerTypeEnum.value_label]


AnswerOutputUnion = Annotated[
    Union[TextAnswerOutput, TimeAnswerOutput, DateAnswerOutput, ValueLabelAnswerOutput],
    Field(discriminator="type"),
]


class QuestionOutput(BaseOutputModel):
    text: str


class TextAnswerQuestionOutput(TextAnswerOutput):
    question: QuestionOutput


class TimeAnswerQuestionOutput(TimeAnswerOutput):
    question: QuestionOutput


class DateAnswerQuestionOutput(DateAnswerOutput):
    question: QuestionOutput


class ValueLabelAnswerQuestionOutput(ValueLabelAnswerOutput):
    question: QuestionOutput


AnswerQuestionOutputUnion = Annotated[
    Union[TextAnswerQuestionOutput, TimeAnswerQuestionOutput, DateAnswerQuestionOutput, ValueLabelAnswerQuestionOutput],
    Field(discriminator="type"),
]


class AttachmentOutput(BaseOutputModel):
    original_filename: str


class UserOutput(BaseOutputModel):
    email: str
    username: str


class AssetOutput(BaseOutputModel):
    external_id: str


class StatesOutput(BaseModel):
    states: list[str]
