from datetime import datetime
from typing import Union

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_jsonlogic import JSONLogic

### Form.io ###


class BaseFormOutput(BaseModel):
    id: int
    title: str
    display: str
    created_at: datetime
    updated_at: datetime


class SimpleStaticFormOutput(BaseModel):
    type: str
    title: str
    display: str
    created_at: datetime
    updated_at: datetime


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
        ]
    ]


class BaseFormPanelComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str

    key: str
    type: str
    input: bool

    position: int


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
        ]
    ]


class FormComponentOutputValidate(BaseModel):
    json_: JSONLogic = Field(alias="json")


class BaseFormComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str
    description: str

    key: str
    type: str
    input: bool

    position: int

    validate_: FormComponentOutputValidate | None = Field(alias="validate", default=None)


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
